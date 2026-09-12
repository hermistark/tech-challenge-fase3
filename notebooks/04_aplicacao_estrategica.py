# Databricks notebook source
# MAGIC %md
# MAGIC # 04: Aplicacao estrategica
# MAGIC
# MAGIC Objetivo: ir alem da metrica de modelo e responder as perguntas de
# MAGIC negocio do edital, usando o modelo treinado em `02_modelagem` para
# MAGIC estimar risco educacional por municipio e UF.
# MAGIC
# MAGIC Perguntas a responder:
# MAGIC 1. Quais fatores mais impactam a alfabetizacao?
# MAGIC 2. Quais municipios apresentam maior risco educacional?
# MAGIC 3. Quais regioes possuem padroes semelhantes?
# MAGIC 4. Como prever municipios que podem nao atingir metas futuras?
# MAGIC 5. Quais variaveis possuem maior influencia nos modelos?

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------
import sys

sys.path.append("..")

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import seaborn as sns

from src.preprocessing.features import select_features

CATALOG = "workspace"
EXCLUDED_FEATURES = ["presenca_lp", "preenchimento_lp", "serie"]

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Carrega modelo e dados

# COMMAND ----------
mlflow.set_experiment("/Shared/fase3_alfabetizacao_aluno")
runs = mlflow.search_runs(order_by=["start_time DESC"], max_results=1)
if runs.empty:
    raise RuntimeError("Nenhuma execucao encontrada. Rode 02_modelagem.py primeiro.")

run_id = runs.iloc[0]["run_id"]
pipeline = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno").toPandas()
X, y = select_features(frame, excluded=EXCLUDED_FEATURES)

print(f"Modelo carregado da execucao {run_id}. Base: {len(frame):,} alunos.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Score de risco por aluno
# MAGIC
# MAGIC Probabilidade prevista de **nao** ser alfabetizado. Quanto mais perto
# MAGIC de 1, maior o risco educacional daquele aluno segundo o modelo.

# COMMAND ----------
frame = frame.reset_index(drop=True)
X = X.reset_index(drop=True)

probabilidades = pipeline.predict_proba(X)[:, 1]
frame["prob_alfabetizado"] = probabilidades
frame["risco_educacional"] = 1 - probabilidades

print("Distribuicao do risco educacional previsto:")
frame["risco_educacional"].describe()

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Pergunta: quais municipios apresentam maior risco educacional?
# MAGIC
# MAGIC Agrega o risco no nivel municipio (media do risco entre os alunos
# MAGIC daquele municipio), so considerando municipios com uma amostra minima
# MAGIC de alunos para o numero nao ser dominado por acaso estatistico.

# COMMAND ----------
MINIMO_ALUNOS_MUNICIPIO = 10

risco_municipio = (
    frame.groupby("id_municipio")
    .agg(
        alunos=("risco_educacional", "count"),
        risco_medio=("risco_educacional", "mean"),
        taxa_alfabetizacao_real=("alfabetizado_oficial", "mean"),
    )
    .reset_index()
)
risco_municipio = risco_municipio[risco_municipio["alunos"] >= MINIMO_ALUNOS_MUNICIPIO]

maior_risco = risco_municipio.sort_values("risco_medio", ascending=False).head(15)
print(f"Top 15 municipios de maior risco (minimo {MINIMO_ALUNOS_MUNICIPIO} alunos avaliados pelo modelo):")
maior_risco

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Pergunta: quais regioes possuem padroes semelhantes?
# MAGIC
# MAGIC Agrupa o risco medio por UF, como uma aproximacao simples de
# MAGIC clusterizacao territorial (UFs com risco medio parecido tendem a ter
# MAGIC padroes semelhantes de resultado).

# COMMAND ----------
if "sigla_uf" in frame.columns:
    risco_uf = (
        frame.groupby("sigla_uf")
        .agg(
            alunos=("risco_educacional", "count"),
            risco_medio=("risco_educacional", "mean"),
        )
        .reset_index()
        .sort_values("risco_medio", ascending=False)
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=risco_uf, y="sigla_uf", x="risco_medio", ax=ax, color="#C44E52")
    ax.set_title("Risco educacional medio previsto, por UF")
    plt.tight_layout()
    plt.show()

    # Agrupamento simples em 3 faixas de risco, como proxy de "padroes semelhantes"
    risco_uf["faixa_risco"] = pd.qcut(
        risco_uf["risco_medio"], q=3, labels=["Risco menor", "Risco intermediario", "Risco maior"]
    )

    print("UFs agrupadas por faixa de risco semelhante:")
    for faixa in ["Risco maior", "Risco intermediario", "Risco menor"]:
        ufs_da_faixa = risco_uf[risco_uf["faixa_risco"] == faixa]["sigla_uf"].tolist()
        print(f"  {faixa}: {', '.join(ufs_da_faixa)}")
else:
    print("Coluna sigla_uf nao encontrada na base carregada, pulando agrupamento por UF.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Pergunta: como prever municipios que podem nao atingir metas futuras?
# MAGIC
# MAGIC Abordagem: usar o risco medio previsto pelo modelo como um indicador
# MAGIC antecipado (proxy) de probabilidade de nao atingimento de meta, dado
# MAGIC que `meta_vs_resultado` teve problemas de preenchimento identificados
# MAGIC na EDA (secao 11 de `01_eda.py`) e nao pode ser usada diretamente como
# MAGIC validacao nesta amostra.

# COMMAND ----------
LIMIAR_ALERTA = risco_municipio["risco_medio"].quantile(0.75)

municipios_alerta = risco_municipio[risco_municipio["risco_medio"] >= LIMIAR_ALERTA]

print(
    f"Usando o percentil 75 do risco medio como limiar de alerta "
    f"({LIMIAR_ALERTA:.2%}): {len(municipios_alerta)} municipios "
    f"(de {len(risco_municipio)} com amostra minima) entrariam em alerta "
    "preventivo de risco de nao atingir metas futuras de alfabetizacao."
)
print(
    "\nRessalva importante: isso e um proxy baseado no modelo atual, nao "
    "uma validacao contra meta oficial. Validar contra meta_vs_resultado "
    "assim que o preenchimento desses campos for corrigido na fonte."
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Perguntas: quais fatores mais impactam, e quais variaveis tem maior influencia?
# MAGIC
# MAGIC Respondidas em detalhe em `03_interpretabilidade.py` (Feature
# MAGIC Importance + SHAP). Resumo executivo aqui:

# COMMAND ----------
print(
    """
Resumo executivo (fatores de maior impacto, detalhe completo em 03):

1. Escola (id_escola / efeito escolar): a EDA e a interpretabilidade do
   modelo convergem no mesmo achado - a escola concentra parte relevante
   da diferenca de resultado, mesmo controlando presenca e preenchimento
   validos na avaliacao.
2. Territorio (sigla_uf / regiao): diferenca persiste mesmo depois de
   isolar apenas alunos efetivamente avaliados.
3. Rede de ensino: impacto secundario e inconsistente entre UFs, nao e um
   fator isolado suficiente para explicar o resultado.

Implicacao para politica publica: intervencao dirigida a escolas e
territorios especificos de maior risco (secao 3 e 4 acima) tende a ser
mais efetiva do que uma politica uniforme por rede de ensino.
"""
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Limitacoes desta aplicacao estrategica

# COMMAND ----------
print(
    """
- O "risco educacional" e uma probabilidade de modelo, nao uma medida
  causal: nao afirma que a escola ou o municipio "causam" o resultado.
- meta_vs_resultado nao pode validar o alerta preventivo nesta amostra
  (problema de preenchimento identificado na EDA).
- A base de modelagem ainda nao incorpora enriquecimento socioeconomico
  (FUNDEB, PNAD, Censo Escolar), documentado como gap em
  data/ENRIQUECIMENTO_E_FEATURES.md. O ranking de risco por municipio
  deve ser tratado como uma primeira aproximacao, a ser refinada quando
  esse enriquecimento for incorporado ao pipeline de features.
"""
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Retorno para o pipeline runner (se houver)

# COMMAND ----------
dbutils.notebook.exit(
    f"Aplicacao estrategica concluida: {len(municipios_alerta)} municipios em alerta preventivo"
)
