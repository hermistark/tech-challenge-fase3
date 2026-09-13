# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # 03: Interpretabilidade
# MAGIC
# MAGIC Objetivo: identificar quais variaveis mais influenciam a predicao de
# MAGIC `alfabetizado_oficial`, e traduzir isso em linguagem de negocio, nao so
# MAGIC em grafico. Usa o modelo treinado em `02_modelagem` (recarregado do
# MAGIC MLflow, para nao depender de rodar os dois notebooks na mesma sessao).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------

#%pip install shap

# COMMAND ----------

# DBTITLE 1,Cell 4


import sys

sys.path.append("..")

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns
import shap

from src.preprocessing.features import select_features

CATALOG = "workspace"
EXCLUDED_FEATURES = [
    "presenca_lp",
    "preenchimento_lp",
    "serie",
    "id_municipio",
    "nome_municipio",
    "capital",
    "record_id",
    "id_aluno",
    "processed_at",
    "schema_version",
    "source",
    "fonte_dados",
    "uf_consistente",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carrega o modelo mais recente do MLflow
# MAGIC
# MAGIC Evita repetir o treino aqui, o objetivo deste notebook e explicar o
# MAGIC modelo ja treinado e registrado em `02_modelagem`.

# COMMAND ----------

mlflow.set_experiment("/Shared/fase3_alfabetizacao_aluno")

runs = mlflow.search_runs(order_by=["start_time DESC"], max_results=1)
if runs.empty:
    raise RuntimeError(
        "Nenhuma execucao encontrada em /Shared/fase3_alfabetizacao_aluno. "
        "Rode 02_modelagem.py primeiro."
    )

run_id = runs.iloc[0]["run_id"]
pipeline = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
print(f"Modelo carregado da execucao: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Recarrega os dados (mesmo recorte de `02_modelagem`)

# COMMAND ----------

try:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno_enriquecida").toPandas()
    print("Usando base ENRIQUECIDA com FUNDEB (gold.base_modelagem_aluno_enriquecida).")
except Exception:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno").toPandas()
    print(
        "AVISO: gold.base_modelagem_aluno_enriquecida nao encontrada. "
        "Usando base sem enriquecimento FUNDEB."
    )

X, y = select_features(frame, excluded=EXCLUDED_FEATURES)

# Amostra para SHAP. Com max_depth=15 (limitado em src/modeling/pipeline.py
# apos o travamento de 29+ minutos com arvore sem limite de profundidade),
# o calculo deve ficar bem mais rapido. Comecando com 1000 linhas; se
# rodar rapido, pode subir; se ainda estiver lento, volte para 300 ou 100.
AMOSTRA_SHAP = 1000
X_amostra = X.sample(n=min(AMOSTRA_SHAP, len(X)), random_state=42)

print(f"Base completa: {len(X):,} linhas. Amostra para SHAP: {len(X_amostra):,} linhas.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Feature importance nativa do RandomForest
# MAGIC
# MAGIC Rapida de calcular, mas nao decompoe por instancia individual, so da
# MAGIC uma visao agregada de quais features o modelo usou mais.

# COMMAND ----------

# DBTITLE 1,Cell 10
preprocessor = pipeline.named_steps["preprocessor"]
modelo = pipeline.named_steps["model"]

# O modelo foi treinado com n_jobs=-1 (paralelo). O SHAP usa o proprio
# modelo internamente, e esse paralelismo, dentro do driver do Databricks,
# e o que provavelmente esta causando o travamento de 29+ minutos mesmo
# com a amostra reduzida para 300 linhas. Forcar execucao serial aqui
# nao muda o modelo treinado, so como o SHAP consulta ele.
modelo.n_jobs = 1

nomes_features = preprocessor.get_feature_names_out()
nomes_features = [
    f.replace("numeric__", "").replace("categorical__", "")
    for f in nomes_features
]
importancias = pd.DataFrame(
    {"feature": nomes_features, "importancia": modelo.feature_importances_}
).sort_values("importancia", ascending=False)

sns.set_style("whitegrid")
fig, ax = plt.subplots(figsize=(10, 8))
top15 = importancias.head(15)

# Cria gradiente de cores
colors = plt.cm.viridis(top15["importancia"][::-1] / top15["importancia"].max())

bars = ax.barh(top15["feature"][::-1], top15["importancia"][::-1], color=colors, edgecolor="white", linewidth=0.5)

# Adiciona valores nas barras
for bar, (_, row) in zip(bars, top15[::-1].iterrows()):
    width = bar.get_width()
    ax.text(width + 0.001, bar.get_y() + bar.get_height() / 2, f"{width:.4f}", ha="left", va="center", fontsize=9, color="#333")

ax.set_xlabel("Importancia", fontsize=10, labelpad=8)
ax.set_ylabel("")
ax.set_title("Top 15 Features por Importancia (RandomForest)", fontsize=13, fontweight="bold", pad=12)
ax.set_xlim(0, top15["importancia"].max() * 1.2)
ax.tick_params(axis="y", labelsize=9)
ax.tick_params(axis="x", labelsize=8)
ax.xaxis.grid(True, alpha=0.3)
ax.yaxis.grid(False)

sns.despine(left=True, bottom=True)
plt.tight_layout()
plt.show()

# Exibe tabela formatada
print("\nTop 15 Features (valores exatos):\n")
print(importancias.head(15).to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. SHAP values
# MAGIC
# MAGIC Decompoe a predicao de cada aluno na contribuicao de cada feature,
# MAGIC permitindo tanto uma visao agregada (summary plot) quanto explicacoes
# MAGIC individuais.

# COMMAND ----------

X_transformado = preprocessor.transform(X_amostra)
if hasattr(X_transformado, "toarray"):
    X_transformado = X_transformado.toarray()

explainer = shap.TreeExplainer(modelo)
shap_values = explainer.shap_values(X_transformado, check_additivity=False)

# Para classificacao binaria, shap_values pode vir como lista [classe_0, classe_1]
# ou como array 3D dependendo da versao do shap; normaliza para a classe positiva.
if isinstance(shap_values, list):
    shap_values_classe_1 = shap_values[1]
elif shap_values.ndim == 3:
    shap_values_classe_1 = shap_values[:, :, 1]
else:
    shap_values_classe_1 = shap_values

print(f"SHAP values calculados para {X_transformado.shape[0]} instancias, {X_transformado.shape[1]} features transformadas.")

# COMMAND ----------

# DBTITLE 1,Cell 13
plt.figure(figsize=(10, 9))
shap.summary_plot(
    shap_values_classe_1,
    X_transformado,
    feature_names=nomes_features,
    show=False,
    max_display=20,
    cmap=plt.cm.coolwarm,
    alpha=0.8
)
plt.title("SHAP Summary Plot - Impacto das Features na Predicao", fontsize=13, fontweight="bold", pad=15)
plt.xlabel("Impacto SHAP (log-odds)", fontsize=10)
plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Leitura de negocio
# MAGIC
# MAGIC Traduz as top features (por SHAP e por importancia nativa) em
# MAGIC linguagem que faz sentido para um gestor educacional, nao so o nome
# MAGIC tecnico da coluna.

# COMMAND ----------

# DBTITLE 1,Cell 15
shap_medio_absoluto = pd.DataFrame(
    {
        "feature": nomes_features,
        "impacto_medio_shap": np.abs(shap_values_classe_1).mean(axis=0),
    }
).sort_values("impacto_medio_shap", ascending=False)

top5_shap = shap_medio_absoluto.head(5).reset_index(drop=True)
print("\n" + "="*60)
print("Top 5 Features por Impacto Medio (SHAP)")
print("="*60)
for i, row in top5_shap.iterrows():
    print(f"  {i+1}. {row['feature']:45s} {row['impacto_medio_shap']:.6f}")
print("="*60)

print(
    """
Leitura de negocio (ajustar apos ver os nomes reais das top5 acima, o
comentario cobre os padroes mais prováveis dado o que a EDA já mostrou):

- Se `id_escola` ou colunas derivadas dela aparecerem no topo: confirma o
  achado da EDA de que a escola concentra grande parte da diferenca de
  resultado. Do ponto de vista de politica publica, isso aponta para
  intervencao focada em escolas especificas, nao so em rede ou regiao.
- Se `sigla_uf` ou `regiao` aparecerem no topo: reforca que o territorio
  continua relevante mesmo depois de excluir presenca/preenchimento, o
  que sustenta politicas de alocacao de recurso por UF/regiao.
- Se `rede`/`rede_label` tiver impacto baixo: consistente com a EDA, que
  ja mostrou que nenhuma rede e superior de forma consistente entre UFs.
"""
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Retorno para o pipeline runner (se houver)

# COMMAND ----------

dbutils.notebook.exit(
    f"Interpretabilidade concluida: top feature (SHAP) = {top5_shap.iloc[0]['feature']}"
)