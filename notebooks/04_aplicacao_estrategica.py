# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
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
# MAGIC Probabilidade prevista de **não** ser alfabetizado. Quanto mais perto
# MAGIC de 1, maior o risco educacional daquele aluno segundo o modelo.

# COMMAND ----------

frame = frame.reset_index(drop=True)
X = X.reset_index(drop=True)

colunas_enriquecimento = [
    "instituicoes_conveniadas",
    "alunos_conveniadas",
    "instituicoes_aee",
    "alunos_aee",
    "instituicoes_profissional",
    "alunos_profissional",
]
for col in colunas_enriquecimento:
    if col not in X.columns:
        X[col] = 0

probabilidades = pipeline.predict_proba(X)[:, 1]
frame["prob_alfabetizado"] = probabilidades
frame["risco_educacional"] = 1 - probabilidades

print("Distribuicao do risco educacional previsto:")
frame["risco_educacional"].describe()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Pergunta: quais municipios apresentam maior risco educacional?
# MAGIC
# MAGIC Aqui não usamos o `id_municipio` do grão de aluno (anonimizado, já
# MAGIC documentado na EDA e sem valor prático para um gestor decidir onde
# MAGIC agir). Usamos o mart `gold.indicador_municipio`, construido na Fase 2
# MAGIC a partir da fonte oficial do INEP, que tem municipio **nomeado** e
# MAGIC taxa de alfabetização **observada** (nao prevista pelo modelo). Essa
# MAGIC e a fonte certa para responder "onde agir", com nome real.

# COMMAND ----------

indicador_municipio = spark.sql(f"""
    SELECT nome_municipio, sigla_uf, ano, rede, taxa_alfabetizacao_media
    FROM {CATALOG}.gold.indicador_municipio
    WHERE ano = (SELECT MAX(ano) FROM {CATALOG}.gold.indicador_municipio)
""").toPandas()

maior_risco_real = (
    indicador_municipio.groupby(["nome_municipio", "sigla_uf"])
    .agg(taxa_alfabetizacao_media=("taxa_alfabetizacao_media", "mean"))
    .reset_index()
    .sort_values("taxa_alfabetizacao_media", ascending=True)
)

print(f"Ano de referencia: {indicador_municipio['ano'].max()}")
print("\nTop 15 municipios de MAIOR risco educacional (menor taxa de alfabetizacao observada, dado oficial INEP):")
maior_risco_real.head(15)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Pergunta: quais regioes possuem padroes semelhantes?
# MAGIC
# MAGIC Agrupa o risco médio por UF, como uma aproximação simples de
# MAGIC clusterizacao territorial (UFs com risco médio parecido tendem a ter
# MAGIC padrões semelhantes de resultado).

# COMMAND ----------

if "sigla_uf" in frame.columns:
    risco_uf = (
        frame.groupby("sigla_uf")
        .agg(
            alunos=("risco_educacional", "count"),
            risco_medio=("risco_educacional", "mean"),
        )
        .reset_index()
        .sort_values("risco_medio", ascending=True)
    )

    risco_uf["faixa_risco"] = pd.qcut(
        risco_uf["risco_medio"], q=3, labels=["Risco menor", "Risco intermediario", "Risco maior"]
    )

    cor_faixa = {
        "Risco menor": "#4C9F70",
        "Risco intermediario": "#E8B84E",
        "Risco maior": "#C44E52",
    }
    cores = risco_uf["faixa_risco"].map(cor_faixa)
    risco_medio_global = risco_uf["risco_medio"].mean()

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(10, 8))
    bars = ax.barh(
        risco_uf["sigla_uf"],
        risco_uf["risco_medio"],
        color=cores,
        edgecolor="white",
        linewidth=0.6,
        height=0.7,
    )

    ax.axvline(risco_medio_global, color="#333333", linestyle="--", linewidth=1.2, alpha=0.7, zorder=0)
    ax.text(
        risco_medio_global + 0.003,
        len(risco_uf) - 0.5,
        f"Media: {risco_medio_global:.3f}",
        fontsize=8,
        color="#333333",
        va="top",
    )

    for bar, (_, row) in zip(bars, risco_uf.iterrows()):
        width = bar.get_width()
        ax.text(
            width + 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{width:.3f}  ({int(row['alunos']):,})",
            ha="left",
            va="center",
            fontsize=7.5,
            color="#333333",
        )

    ax.set_xlabel("Risco educacional medio previsto", fontsize=10, labelpad=8)
    ax.set_ylabel("")
    ax.set_title("Risco educacional medio previsto por UF", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, risco_uf["risco_medio"].max() * 1.22)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.xaxis.grid(True, alpha=0.3)
    ax.yaxis.grid(False)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cor_faixa.values()]
    ax.legend(
        handles,
        cor_faixa.keys(),
        title="Faixa de risco",
        loc="lower right",
        fontsize=8,
        title_fontsize=8.5,
        frameon=True,
        framealpha=0.9,
    )

    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    plt.show()

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
# MAGIC `meta_vs_resultado` tem problema de preenchimento identificado na EDA
# MAGIC (secao 11 de `01_eda.py`), entao a abordagem aqui e outra: cruzar o
# MAGIC nivel atual de alfabetizacao (baixo = ja em risco hoje) com a
# MAGIC tendencia observada em `evolucao_temporal` (piorando = risco de
# MAGIC futuro tambem ruim), os dois com nome de municipio real.

# COMMAND ----------

LIMIAR_RISCO_ATUAL = maior_risco_real["taxa_alfabetizacao_media"].quantile(0.25)

municipios_risco_atual = set(
    maior_risco_real[maior_risco_real["taxa_alfabetizacao_media"] <= LIMIAR_RISCO_ATUAL]["nome_municipio"]
)

municipios_alerta_duplo = set()
try:
    tendencia_municipio = spark.sql(f"""
        SELECT nome_municipio, sigla_uf, tendencia
        FROM {CATALOG}.gold.evolucao_temporal
        WHERE nivel_territorial = 'municipio'
        AND ano = (SELECT MAX(ano) FROM {CATALOG}.gold.evolucao_temporal WHERE nivel_territorial = 'municipio')
    """).toPandas()

    municipios_piorando = set(
        tendencia_municipio[tendencia_municipio["tendencia"].str.contains("queda|piora", case=False, na=False)]["nome_municipio"]
    )

    municipios_alerta_duplo = municipios_risco_atual & municipios_piorando

    print(f"Municipios com taxa atual baixa (bottom 25%): {len(municipios_risco_atual)}")
    print(f"Municipios com tendencia de queda: {len(municipios_piorando)}")
    print(f"\nMunicipios em ALERTA DUPLO (baixo hoje E piorando): {len(municipios_alerta_duplo)}")
    if municipios_alerta_duplo:
        print(sorted(municipios_alerta_duplo)[:20])
except Exception as exc:
    print(
        f"Nao foi possivel cruzar com evolucao_temporal ({type(exc).__name__}: {exc}). "
        f"Usando so o criterio de taxa atual baixa: {len(municipios_risco_atual)} municipios "
        "no bottom 25% de alfabetizacao, candidatos a risco de nao atingir metas futuras."
    )

print(
    "\nRessalva: isso e um proxy baseado em nivel e tendencia observados, "
    "nao uma validacao contra meta oficial. meta_vs_resultado nao esta "
    "confiavel nesta amostra ainda; revisitar quando o preenchimento "
    "desses campos for corrigido na fonte."
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
    f"Aplicacao estrategica concluida: {len(municipios_risco_atual)} municipios em risco atual, "
    f"{len(municipios_alerta_duplo)} em alerta duplo (risco atual + tendencia de queda)"
)