# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "databricks_ai_v5"
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # 02: Modelagem supervisionada
# MAGIC
# MAGIC Objetivo: prever `alfabetizado_oficial` (0/1) a partir de
# MAGIC `gold.base_modelagem_aluno`, seguindo os requisitos do edital:
# MAGIC imputacao, encoding, pipeline sklearn unico (pre-processamento dentro
# MAGIC do modelo), tratamento de vazamento, split sem vazamento, validacao
# MAGIC cruzada e metricas de generalizacao.
# MAGIC
# MAGIC Decisoes desta etapa, vindas direto do `01_eda`:
# MAGIC
# MAGIC 1. Target desbalanceado (~60% nao alfabetizado, ~40% alfabetizado) ->
# MAGIC    usar `class_weight="balanced"`, split estratificado, e reportar
# MAGIC    F1/AUC/recall por classe, nunca so accuracy.
# MAGIC 2. `presenca_lp` e `preenchimento_lp` sao excluidas das features por
# MAGIC    decisao explicita: a EDA mostrou que 100% dos alunos alfabetizados
# MAGIC    estao no grupo presenca=1 e preenchimento=1, e 0% dos ausentes sao
# MAGIC    alfabetizados. Isso e vazamento indireto do proprio processo de
# MAGIC    mensuracao do target, nao um fator explicativo real.
# MAGIC 3. `serie` e excluida por nao ter variancia na amostra (100% serie 2).
# MAGIC 4. `VL_PROFICIENCIA_LP` ja vem excluida na origem (Fase 2), mantido
# MAGIC    aqui como camada extra de seguranca.
# MAGIC 5. `id_municipio`, `nome_municipio` e `capital` sao excluidas: a EDA
# MAGIC    ja documentou que `id_municipio` no grao de aluno e anonimizado e
# MAGIC    nao corresponde ao codigo real do IBGE, entao qualquer coluna
# MAGIC    derivada desse join (como `capital`) chega vazia ou nao confiavel.
# MAGIC    `sigla_uf` continua confiavel e e usada no lugar como feature
# MAGIC    territorial.
# MAGIC 6. `record_id` e `id_aluno` sao identificadores unicos (uma linha por
# MAGIC    valor) e nao features preditivas. Incluir isso sem excluir faz o
# MAGIC    encoder tentar criar uma coluna por valor unico, o que explica
# MAGIC    travamentos/demora extrema na validacao cruzada. `processed_at`,
# MAGIC    `schema_version`, `source`, `fonte_dados` e `uf_consistente` sao
# MAGIC    metadado de execucao do pipeline de dados, tambem excluidos por
# MAGIC    nao serem caracteristica do aluno/escola.
# MAGIC 7. `max_depth=15` no RandomForest (`src/modeling/pipeline.py`):
# MAGIC    `id_escola` tem 1181 categorias e vira 1181 colunas apos o
# MAGIC    one-hot, deixando arvores sem limite de profundidade gigantescas.
# MAGIC    Isso travou o calculo de SHAP em `03_interpretabilidade.py`
# MAGIC    (29+ minutos sem terminar mesmo com amostra reduzida). Limitar a
# MAGIC    profundidade tambem reduz risco de overfitting, nao e so uma
# MAGIC    correcao de performance.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------


import sys

sys.path.append("..")

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from src.evaluation.metrics import evaluate_classifier
from src.modeling.pipeline import build_random_forest_pipeline
from src.preprocessing.features import select_features

CATALOG = "workspace"
RANDOM_STATE = 42

# Exclusoes documentadas na celula acima: vazamento indireto + sem variancia.
EXCLUDED_FEATURES = [
    "presenca_lp",
    "preenchimento_lp",
    "serie",
    "id_municipio",
    "nome_municipio",
    "capital",
    # Identificadores unicos (um valor por linha) - nao sao features, e se
    # o encoder tentar tratar como categorico gera dezenas de milhares de
    # colunas novas, explicando travamentos/demora extrema na modelagem.
    "record_id",
    "id_aluno",
    # Metadado do pipeline de dados, nao caracteristica do aluno/escola.
    "processed_at",
    "schema_version",
    "source",
    "fonte_dados",
    "uf_consistente",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carga dos dados
# MAGIC
# MAGIC Tenta usar a base ja enriquecida com FUNDEB (`00_enriquecimento_fundeb.py`);
# MAGIC se ainda nao tiver sido publicada, cai para a base original sem
# MAGIC enriquecimento, e avisa isso explicitamente.

# COMMAND ----------

try:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno_enriquecida").toPandas()
    print("Usando base ENRIQUECIDA com FUNDEB (gold.base_modelagem_aluno_enriquecida).")
except Exception:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno").toPandas()
    print(
        "AVISO: gold.base_modelagem_aluno_enriquecida nao encontrada. "
        "Usando base sem enriquecimento FUNDEB. Rode 00_enriquecimento_fundeb.py "
        "antes deste notebook para incluir o enriquecimento."
    )

print(f"Registros carregados: {len(frame):,}")
print(f"Colunas: {list(frame.columns)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Selecao de features e split
# MAGIC
# MAGIC `select_features` ja remove `VL_PROFICIENCIA_LP` e o proprio target por
# MAGIC padrao (`LEAKAGE_COLUMNS` em `src/preprocessing/features.py`). As
# MAGIC exclusoes adicionais documentadas acima entram via `excluded`.

# COMMAND ----------

X, y = select_features(frame, excluded=EXCLUDED_FEATURES)

print(f"Features usadas ({len(X.columns)}): {list(X.columns)}")
print(f"\nDistribuicao do target:\n{y.value_counts(normalize=True)}")

# COMMAND ----------

# Checagem defensiva: qualquer feature 100% vazia quebra ou gera warning
# no imputer mais na frente. Detecta e avisa AQUI, de forma explicita, em
# vez de deixar aparecer como um warning silencioso do sklearn depois.
colunas_totalmente_vazias = [c for c in X.columns if X[c].isna().all()]
if colunas_totalmente_vazias:
    print(
        f"AVISO: {len(colunas_totalmente_vazias)} coluna(s) 100% vazia(s) "
        f"nesta base, removendo automaticamente: {colunas_totalmente_vazias}"
    )
    X = X.drop(columns=colunas_totalmente_vazias)
else:
    print("Nenhuma coluna totalmente vazia encontrada nas features selecionadas.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Split treino/teste: proporcao de Pareto (80/20)
# MAGIC
# MAGIC 80% para treino, 20% para teste, estratificado pelo target (mantem a
# MAGIC mesma proporcao de alfabetizado/nao alfabetizado nos dois conjuntos,
# MAGIC dado o desbalanceamento identificado na EDA).

# COMMAND ----------

PROPORCAO_TREINO = 0.8
PROPORCAO_TESTE = 0.2

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=PROPORCAO_TESTE,
    random_state=RANDOM_STATE,
    stratify=y,
)

print(f"Split Pareto {PROPORCAO_TREINO:.0%}/{PROPORCAO_TESTE:.0%}")
print(f"Treino: {len(X_train):,} | Teste: {len(X_test):,}")
print(f"Proporcao da classe positiva - treino: {y_train.mean():.2%}, teste: {y_test.mean():.2%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Baseline
# MAGIC
# MAGIC `DummyClassifier` com estrategia estratificada: sorteia a classe
# MAGIC respeitando a proporcao observada, sem olhar nenhuma feature. Qualquer
# MAGIC modelo real precisa superar isso para justificar a complexidade.

# COMMAND ----------

baseline = DummyClassifier(strategy="stratified", random_state=RANDOM_STATE)
baseline.fit(X_train, y_train)

# DummyClassifier nao lida com o mesmo ColumnTransformer do pipeline real,
# entao a avaliacao aqui usa so a coluna do target para simular predict_proba.
baseline_pred = baseline.predict(X_test)
baseline_score = (baseline_pred == y_test).mean()
print(f"Baseline (dummy estratificado) - acuracia: {baseline_score:.4f}")
print(
    "Acuracia sozinha nao diz muito aqui, dado o desbalanceamento. "
    "O contraste real com o modelo esta nas metricas da secao 5."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Pipeline de producao: pre-processamento + RandomForest
# MAGIC
# MAGIC `build_random_forest_pipeline` empacota `ColumnTransformer`
# MAGIC (imputacao + scaling nas numericas, imputacao + one-hot nas
# MAGIC categoricas) e o classificador num unico `Pipeline` do sklearn. Isso
# MAGIC garante que as estatisticas de imputacao/scaling sejam aprendidas
# MAGIC somente no treino, nunca vazando informacao do teste.

# COMMAND ----------

pipeline = build_random_forest_pipeline(X_train)
pipeline.fit(X_train, y_train)
print("Pipeline treinado.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Avaliacao no conjunto de teste

# COMMAND ----------

resultado = evaluate_classifier(pipeline, X_test, y_test)

print(f"ROC AUC: {resultado['roc_auc']:.4f}")
print("\nRelatorio de classificacao:")
relatorio = pd.DataFrame(resultado["classification_report"]).transpose()
relatorio

# COMMAND ----------

matriz = np.array(resultado["confusion_matrix"])
print("Matriz de confusao (linhas=real, colunas=previsto):")
print(pd.DataFrame(matriz, index=["real_0", "real_1"], columns=["prev_0", "prev_1"]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Validacao cruzada
# MAGIC
# MAGIC `StratifiedKFold` mantem a proporcao do target em cada fold, essencial
# MAGIC com o desbalanceamento observado na EDA.

# COMMAND ----------

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

cv_resultado = cross_validate(
    pipeline,
    X_train,
    y_train,
    cv=cv,
    scoring=["roc_auc", "f1", "recall", "precision"],
    # n_jobs=1: dentro do driver do Databricks, paralelismo do joblib pode
    # conflitar com o gerenciamento de processos do Spark e travar em vez
    # de acelerar. Com 37 mil linhas nao precisa de paralelismo mesmo.
    n_jobs=1,
)

cv_resumo = pd.DataFrame(cv_resultado)[
    ["test_roc_auc", "test_f1", "test_recall", "test_precision"]
]
cv_resumo.loc["media"] = cv_resumo.mean()
cv_resumo.loc["desvio_padrao"] = cv_resumo.iloc[:-1].std()
cv_resumo

# COMMAND ----------

print(
    f"ROC AUC medio (CV): {cv_resumo.loc['media', 'test_roc_auc']:.4f} "
    f"+/- {cv_resumo.loc['desvio_padrao', 'test_roc_auc']:.4f}\n"
    f"F1 medio (CV): {cv_resumo.loc['media', 'test_f1']:.4f} "
    f"+/- {cv_resumo.loc['desvio_padrao', 'test_f1']:.4f}"
)
print(
    "Desvio padrao baixo entre folds indica generalizacao estavel, nao "
    "so um resultado de sorte do split treino/teste escolhido."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Registro no MLflow

# COMMAND ----------

import mlflow
import mlflow.sklearn

mlflow.set_experiment("/Shared/fase3_alfabetizacao_aluno")

with mlflow.start_run(run_name="random_forest_aluno"):
    mlflow.log_param("modelo", "RandomForestClassifier")
    mlflow.log_param("n_estimators", 200)
    mlflow.log_param("max_depth", 15)
    mlflow.log_param("features_excluidas", EXCLUDED_FEATURES)
    mlflow.log_param("n_features", len(X.columns))
    mlflow.log_param("n_treino", len(X_train))
    mlflow.log_param("n_teste", len(X_test))

    mlflow.log_metric("roc_auc_teste", resultado["roc_auc"])
    mlflow.log_metric("roc_auc_cv_media", cv_resumo.loc["media", "test_roc_auc"])
    mlflow.log_metric("f1_cv_media", cv_resumo.loc["media", "test_f1"])
    mlflow.log_metric("recall_cv_media", cv_resumo.loc["media", "test_recall"])

    input_example = X_train.head(5)
    mlflow.sklearn.log_model(pipeline, "model", input_example=input_example)

    print("Execucao registrada no MLflow: /Shared/fase3_alfabetizacao_aluno")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Retorno para o pipeline runner (se houver)

# COMMAND ----------

dbutils.notebook.exit(
    f"Modelagem concluida: roc_auc_teste={resultado['roc_auc']:.4f}, "
    f"roc_auc_cv={cv_resumo.loc['media', 'test_roc_auc']:.4f}"
)