# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# dependencies = [
#   "shap",
# ]
# ///
# MAGIC %md
# MAGIC # 05: Dashboard executivo - Predicao de Alfabetizacao
# MAGIC
# MAGIC Consolida em um so lugar o que os notebooks anteriores produziram:
# MAGIC visao geral dos dados, performance do modelo, interpretabilidade
# MAGIC (Feature Importance + SHAP) e aplicacao estrategica (risco por
# MAGIC municipio/UF). Nao recalcula nada do zero: le o modelo do MLflow e
# MAGIC os dados da Gold, os mesmos que `02_modelagem.py`,
# MAGIC `03_interpretabilidade.py` e `04_aplicacao_estrategica.py` usam.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------

#%pip install shap

# COMMAND ----------

import base64
import io
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

plt.style.use("dark_background")
COR_FUNDO_GRAFICO = "#0b1728"
COR_GRID = "#1a2b42"
COR_TEXTO_GRAFICO = "#c9d6e8"

plt.rcParams.update({
    "figure.facecolor": COR_FUNDO_GRAFICO,
    "axes.facecolor": COR_FUNDO_GRAFICO,
    "axes.edgecolor": COR_GRID,
    "axes.labelcolor": COR_TEXTO_GRAFICO,
    "text.color": COR_TEXTO_GRAFICO,
    "xtick.color": COR_TEXTO_GRAFICO,
    "ytick.color": COR_TEXTO_GRAFICO,
    "grid.color": COR_GRID,
    "font.family": "sans-serif",
})


def figura_para_base64() -> str:
    """Converte a figura matplotlib atual em imagem embutida no HTML, mantendo o fundo escuro."""
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100, facecolor=COR_FUNDO_GRAFICO)
    plt.close()
    buffer.seek(0)
    codificado = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{codificado}"


def tabela_html(df: pd.DataFrame) -> str:
    """
    Gera uma tabela HTML com estilo inline em cada celula, em vez de
    depender de CSS externo. df.to_html() sozinho ficava ilegivel dentro
    do displayHTML do Databricks (o notebook aplica seu proprio estilo de
    tabela por cima, com fundo claro e texto quase invisivel no tema
    escuro). Inline style tem prioridade mais alta e nao sofre esse
    conflito.
    """
    estilo_th = "background:#101f34;color:#8fa2bd;padding:8px 12px;text-align:left;border:1px solid #1a2b42;font-size:10px;text-transform:uppercase;letter-spacing:.05em;"
    estilo_td = "background:#0b1728;color:#f4f8ff;padding:8px 12px;text-align:left;border:1px solid #1a2b42;font-size:12px;"

    cabecalho = "".join(f'<th style="{estilo_th}">{col}</th>' for col in df.columns)
    linhas = ""
    for _, linha in df.iterrows():
        celulas = "".join(f'<td style="{estilo_td}">{valor}</td>' for valor in linha)
        linhas += f"<tr>{celulas}</tr>"

    return f'<table style="border-collapse:collapse;width:100%;"><thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table>'

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carrega modelo e dados

# COMMAND ----------

mlflow.set_experiment("/Shared/fase3_alfabetizacao_aluno")
runs = mlflow.search_runs(order_by=["start_time DESC"], max_results=1)
if runs.empty:
    raise RuntimeError("Nenhuma execucao encontrada. Rode 02_modelagem.py primeiro.")

run = runs.iloc[0]
run_id = run["run_id"]
pipeline = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

try:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno_enriquecida").toPandas()
except Exception:
    frame = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno").toPandas()

frame = frame.reset_index(drop=True)
X, y = select_features(frame, excluded=EXCLUDED_FEATURES)
X = X.reset_index(drop=True)

print(f"Modelo carregado (run {run_id}). Base: {len(frame):,} alunos, {len(X.columns)} features.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. KPIs de visao geral

# COMMAND ----------

probabilidades = pipeline.predict_proba(X)[:, 1]
frame["prob_alfabetizado"] = probabilidades
frame["risco_educacional"] = 1 - probabilidades

kpi_total_alunos = len(frame)
kpi_taxa_alfabetizacao = frame["alfabetizado_oficial"].mean()
kpi_escolas = frame["id_escola"].nunique()
kpi_ufs = frame["sigla_uf"].nunique()
kpi_roc_auc = run.get("metrics.roc_auc_teste", float("nan"))
kpi_roc_auc_cv = run.get("metrics.roc_auc_cv_media", float("nan"))
kpi_f1_cv = run.get("metrics.f1_cv_media", float("nan"))

print(f"Alunos: {kpi_total_alunos:,} | Taxa de alfabetizacao: {kpi_taxa_alfabetizacao:.1%}")
print(f"Escolas: {kpi_escolas:,} | UFs: {kpi_ufs}")
print(f"ROC AUC (teste): {kpi_roc_auc:.4f} | ROC AUC (CV media): {kpi_roc_auc_cv:.4f} | F1 (CV media): {kpi_f1_cv:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Grafico: distribuicao do risco educacional

# COMMAND ----------

# DBTITLE 1,Cell 10 - Distribuicao risco
fig, ax = plt.subplots(figsize=(9, 5))
sns.histplot(frame["risco_educacional"], bins=30, ax=ax, color="#ff7181", edgecolor=COR_FUNDO_GRAFICO, linewidth=0.5)
ax.axvline(frame["risco_educacional"].mean(), color=COR_TEXTO_GRAFICO, linestyle="--", linewidth=1.2, alpha=0.7)
ax.text(frame["risco_educacional"].mean() + 0.003, ax.get_ylim()[1] * 0.92, f"Media: {frame['risco_educacional'].mean():.3f}", fontsize=8, color=COR_TEXTO_GRAFICO, va="top")
ax.set_title("Distribuicao do risco educacional previsto pelo modelo", fontsize=12, fontweight="bold", pad=10)
ax.set_xlabel("Risco (1 - probabilidade de alfabetizacao)", fontsize=9)
ax.set_ylabel("Numero de alunos", fontsize=9)
ax.xaxis.grid(True, alpha=0.25)
ax.yaxis.grid(True, alpha=0.25)
sns.despine(left=True, bottom=True)
img_distribuicao_risco = figura_para_base64()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Grafico: risco medio por UF

# COMMAND ----------

# DBTITLE 1,Cell 12 - Risco por UF
risco_uf = (
    frame.groupby("sigla_uf")
    .agg(alunos=("risco_educacional", "count"), risco_medio=("risco_educacional", "mean"))
    .reset_index()
    .sort_values("risco_medio", ascending=True)
)

risco_uf["faixa_risco"] = pd.qcut(
    risco_uf["risco_medio"], q=3, labels=["Risco menor", "Risco intermediario", "Risco maior"]
)

cor_faixa = {
    "Risco menor": "#43dda6",
    "Risco intermediario": "#f4c761",
    "Risco maior": "#ff7181",
}
cores = risco_uf["faixa_risco"].map(cor_faixa)
risco_medio_global = risco_uf["risco_medio"].mean()

fig, ax = plt.subplots(figsize=(10, 8))
bars = ax.barh(
    risco_uf["sigla_uf"],
    risco_uf["risco_medio"],
    color=cores,
    edgecolor=COR_FUNDO_GRAFICO,
    linewidth=0.6,
    height=0.7,
)

ax.axvline(risco_medio_global, color=COR_TEXTO_GRAFICO, linestyle="--", linewidth=1.2, alpha=0.7, zorder=0)
ax.text(risco_medio_global + 0.003, len(risco_uf) - 0.5, f"Media: {risco_medio_global:.3f}", fontsize=8, color=COR_TEXTO_GRAFICO, va="top")

for bar, (_, row) in zip(bars, risco_uf.iterrows()):
    width = bar.get_width()
    ax.text(width + 0.005, bar.get_y() + bar.get_height() / 2, f"{width:.3f}  ({int(row['alunos']):,})", ha="left", va="center", fontsize=7.5, color=COR_TEXTO_GRAFICO)

ax.set_xlabel("Risco educacional medio previsto", fontsize=9, labelpad=8)
ax.set_ylabel("")
ax.set_title("Risco educacional medio previsto por UF", fontsize=12, fontweight="bold", pad=12)
ax.set_xlim(0, risco_uf["risco_medio"].max() * 1.22)
ax.tick_params(axis="y", labelsize=8)
ax.tick_params(axis="x", labelsize=7.5)
ax.xaxis.grid(True, alpha=0.25)
ax.yaxis.grid(False)

handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cor_faixa.values()]
ax.legend(handles, cor_faixa.keys(), title="Faixa de risco", loc="lower right", fontsize=8, title_fontsize=8.5, frameon=True, framealpha=0.7)

sns.despine(left=True, bottom=True)
img_risco_uf = figura_para_base64()

tabela_risco_uf_formatada = risco_uf.sort_values("risco_medio", ascending=False).head(10).copy()
tabela_risco_uf_formatada["risco_medio"] = tabela_risco_uf_formatada["risco_medio"].apply(lambda v: f"{v:.1%}")
tabela_risco_uf_html = tabela_html(tabela_risco_uf_formatada)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4b. Municipios de maior risco (dado oficial nomeado, nao anonimizado)
# MAGIC
# MAGIC Usa `gold.indicador_municipio` (Fase 2, INEP), com nome real de
# MAGIC municipio, em vez do `id_municipio` anonimizado do grao de aluno.
# MAGIC Mesma logica de `04_aplicacao_estrategica.py`.

# COMMAND ----------

indicador_municipio = spark.sql(f"""
    SELECT nome_municipio, sigla_uf, ano, taxa_alfabetizacao_media
    FROM {CATALOG}.gold.indicador_municipio
    WHERE ano = (SELECT MAX(ano) FROM {CATALOG}.gold.indicador_municipio)
""").toPandas()

maior_risco_municipio_real = (
    indicador_municipio.groupby(["nome_municipio", "sigla_uf"])
    .agg(taxa_alfabetizacao_media=("taxa_alfabetizacao_media", "mean"))
    .reset_index()
    .sort_values("taxa_alfabetizacao_media", ascending=True)
    .head(15)
)

tabela_municipio_formatada = maior_risco_municipio_real.copy()
tabela_municipio_formatada["taxa_alfabetizacao_media"] = tabela_municipio_formatada["taxa_alfabetizacao_media"].apply(lambda v: f"{v:.1%}")
tabela_municipio_formatada.columns = ["Municipio", "UF", "Taxa de alfabetizacao"]
tabela_municipio_real_html = tabela_html(tabela_municipio_formatada)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Grafico: Feature Importance

# COMMAND ----------

# DBTITLE 1,Cell 16 - Feature Importance
preprocessor = pipeline.named_steps["preprocessor"]
modelo = pipeline.named_steps["model"]
modelo.n_jobs = 1

nomes_features = preprocessor.get_feature_names_out()
nomes_features = [
    f.replace("numeric__", "").replace("categorical__", "")
    for f in nomes_features
]
importancias = pd.DataFrame(
    {"feature": nomes_features, "importancia": modelo.feature_importances_}
).sort_values("importancia", ascending=False)

fig, ax = plt.subplots(figsize=(10, 8))
top15 = importancias.head(15)

colors = plt.cm.viridis(top15["importancia"][::-1] / top15["importancia"].max())
bars = ax.barh(top15["feature"][::-1], top15["importancia"][::-1], color=colors, edgecolor=COR_FUNDO_GRAFICO, linewidth=0.5)

for bar, (_, row) in zip(bars, top15[::-1].iterrows()):
    width = bar.get_width()
    ax.text(width + 0.001, bar.get_y() + bar.get_height() / 2, f"{width:.4f}", ha="left", va="center", fontsize=8, color=COR_TEXTO_GRAFICO)

ax.set_xlabel("Importancia", fontsize=9, labelpad=8)
ax.set_ylabel("")
ax.set_title("Top 15 features por importancia (RandomForest)", fontsize=12, fontweight="bold", pad=12)
ax.set_xlim(0, top15["importancia"].max() * 1.2)
ax.tick_params(axis="y", labelsize=8)
ax.tick_params(axis="x", labelsize=7.5)
ax.xaxis.grid(True, alpha=0.25)
ax.yaxis.grid(False)
sns.despine(left=True, bottom=True)
img_feature_importance = figura_para_base64()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Grafico: SHAP summary

# COMMAND ----------

# DBTITLE 1,Cell 18 - SHAP summary
AMOSTRA_SHAP = 1000
X_amostra = X.sample(n=min(AMOSTRA_SHAP, len(X)), random_state=42)
X_transformado = preprocessor.transform(X_amostra)
if hasattr(X_transformado, "toarray"):
    X_transformado = X_transformado.toarray()

explainer = shap.TreeExplainer(modelo)
shap_values = explainer.shap_values(X_transformado, check_additivity=False)

if isinstance(shap_values, list):
    shap_values_classe_1 = shap_values[1]
elif shap_values.ndim == 3:
    shap_values_classe_1 = shap_values[:, :, 1]
else:
    shap_values_classe_1 = shap_values

plt.figure(figsize=(10, 8))
shap.summary_plot(
    shap_values_classe_1, X_transformado, feature_names=nomes_features,
    show=False, max_display=20, cmap=plt.cm.coolwarm, alpha=0.8
)
plt.title("SHAP summary - impacto das features na predicao", fontsize=12, fontweight="bold", pad=15)
plt.xlabel("Impacto SHAP (log-odds)", fontsize=9)
img_shap = figura_para_base64()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Detalhamento por escola
# MAGIC
# MAGIC Nota de qualidade de dado: `id_municipio`/`nome_municipio` no grao de
# MAGIC aluno sao anonimizados (ja documentado em `01_eda.py`, secao 14), por
# MAGIC isso essa aba mostra escola + UF, nao escola + municipio. UF e o
# MAGIC territorio confiavel nesse grao.

# COMMAND ----------

escolas_detalhado = (
    frame[(frame["presenca_lp"] == 1) & (frame["preenchimento_lp"] == 1)]
    .groupby(["id_escola", "sigla_uf"])
    .agg(
        alunos_avaliados=("alfabetizado_oficial", "count"),
        taxa_alfabetizacao=("alfabetizado_oficial", "mean"),
        risco_medio=("risco_educacional", "mean"),
    )
    .reset_index()
)
escolas_detalhado = escolas_detalhado[escolas_detalhado["alunos_avaliados"] >= 10]

print(f"Escolas com pelo menos 10 alunos avaliados: {len(escolas_detalhado):,}")


def formatar_tabela_escolas(df_escolas: pd.DataFrame) -> str:
    formatada = df_escolas.copy()
    formatada["taxa_alfabetizacao"] = (formatada["taxa_alfabetizacao"] * 100).round(1).astype(str) + "%"
    formatada["risco_medio"] = (formatada["risco_medio"] * 100).round(1).astype(str) + "%"
    formatada.columns = ["ID Escola", "UF", "Alunos avaliados", "Taxa alfabetizacao", "Risco medio"]
    return tabela_html(formatada)


piores_escolas_html = formatar_tabela_escolas(
    escolas_detalhado.sort_values("risco_medio", ascending=False).head(20)
)
melhores_escolas_html = formatar_tabela_escolas(
    escolas_detalhado.sort_values("risco_medio", ascending=True).head(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Monta o HTML final com abas

# COMMAND ----------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
:root {
    --bg-deep: #040a12;
    --surface: #0b1728;
    --surface-2: #101f34;
    --line: rgba(255,255,255,.085);
    --text: #f4f8ff;
    --muted: #8fa2bd;
    --cyan: #43d8e7;
    --violet: #8d7dff;
    --green: #43dda6;
    --amber: #f4c761;
    --red: #ff7181;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    margin: 0;
    min-height: 100vh;
    color: var(--text);
    background:
        radial-gradient(circle at 82% -8%, rgba(67,216,231,.08), transparent 26%),
        radial-gradient(circle at 10% 5%, rgba(141,125,255,.07), transparent 28%),
        var(--bg-deep);
    font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
    padding: 24px 28px;
}
.topo { border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 18px; }
.page-kicker { color: var(--cyan); font-size: 9px; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
.page-title { margin-top: 4px; font-size: 22px; font-weight: 900; letter-spacing: -.03em; }
.top-nav { display: flex; gap: 8px; margin-bottom: 22px; flex-wrap: wrap; }
.nav-button {
    padding: 9px 16px; border-radius: 9px; border: 1px solid var(--line);
    background: var(--surface); color: #9dafc7; cursor: pointer;
    font-size: 12px; font-family: inherit; font-weight: 600;
}
.nav-button:hover { color: #fff; background: rgba(255,255,255,.06); }
.nav-button.active {
    color: #fff;
    background: linear-gradient(90deg, rgba(67,216,231,.22), rgba(141,125,255,.14));
    border-color: rgba(67,216,231,.35);
}
.kpi-grid { display: flex; gap: 14px; margin-bottom: 24px; flex-wrap: wrap; }
.kpi-card {
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    padding: 16px 20px; min-width: 150px; flex: 1;
}
.kpi-card .valor { font-size: 24px; font-weight: 800; color: var(--cyan); }
.kpi-card .rotulo { font-size: 10px; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: .06em; }
.tab-content { display: none; }
.tab-content.active { display: block; }
.card {
    background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
    padding: 20px; margin-bottom: 18px;
}
.card h3 { margin-top: 0; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }
img { max-width: 100%; border-radius: 8px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<div class="topo">
  <div class="page-kicker">Tech Challenge - FIAP Pos Tech AI Scientist - Fase 3</div>
  <div class="page-title">Dashboard executivo: Predicao de Alfabetizacao</div>
</div>

<div class="top-nav">
  <button class="nav-button active" onclick="mudarAba(event, 'visao-geral')">Visao geral</button>
  <button class="nav-button" onclick="mudarAba(event, 'modelo')">Modelo</button>
  <button class="nav-button" onclick="mudarAba(event, 'interpretabilidade')">Interpretabilidade</button>
  <button class="nav-button" onclick="mudarAba(event, 'escolas')">Escolas</button>
  <button class="nav-button" onclick="mudarAba(event, 'aplicacao')">Aplicacao estrategica</button>
</div>

<div class="kpi-grid">
  <div class="kpi-card"><div class="valor">__TOTAL_ALUNOS__</div><div class="rotulo">Alunos avaliados</div></div>
  <div class="kpi-card"><div class="valor">__TAXA_ALFABETIZACAO__</div><div class="rotulo">Taxa de alfabetizacao</div></div>
  <div class="kpi-card"><div class="valor">__ESCOLAS__</div><div class="rotulo">Escolas</div></div>
  <div class="kpi-card"><div class="valor">__UFS__</div><div class="rotulo">UFs</div></div>
  <div class="kpi-card"><div class="valor">__ROC_AUC__</div><div class="rotulo">ROC AUC (modelo)</div></div>
</div>

<div id="visao-geral" class="tab-content active">
  <div class="card">
    <h3>Distribuicao do risco educacional previsto</h3>
    <img src="__IMG_DISTRIBUICAO_RISCO__">
  </div>
</div>

<div id="modelo" class="tab-content">
  <div class="card">
    <h3>Metricas do modelo (RandomForestClassifier, max_depth=15)</h3>
    __TABELA_METRICAS__
  </div>
</div>

<div id="interpretabilidade" class="tab-content">
  <div class="grid-2">
    <div class="card">
      <h3>Feature Importance</h3>
      <img src="__IMG_FEATURE_IMPORTANCE__">
    </div>
    <div class="card">
      <h3>SHAP summary</h3>
      <img src="__IMG_SHAP__">
    </div>
  </div>
</div>

<div id="escolas" class="tab-content">
  <div class="card">
    <h3>Nota sobre territorio</h3>
    <p style="color:#8fa2bd;font-size:12px;margin:0;">
      O identificador de municipio no grao de aluno e anonimizado (nao
      corresponde ao codigo real do IBGE), por isso esta aba mostra escola
      cruzada com UF, nao com municipio. UF e o nivel territorial confiavel
      neste grao de dado.
    </p>
  </div>
  <div class="grid-2">
    <div class="card">
      <h3>20 escolas de maior risco (minimo 10 alunos avaliados)</h3>
      __TABELA_PIORES_ESCOLAS__
    </div>
    <div class="card">
      <h3>20 escolas de menor risco (minimo 10 alunos avaliados)</h3>
      __TABELA_MELHORES_ESCOLAS__
    </div>
  </div>
</div>

<div id="aplicacao" class="tab-content">
  <div class="grid-2">
    <div class="card">
      <h3>Risco medio por UF (previsto pelo modelo)</h3>
      <img src="__IMG_RISCO_UF__">
    </div>
    <div class="card">
      <h3>Top 10 UFs por risco</h3>
      __TABELA_RISCO_UF__
    </div>
  </div>
  <div class="card">
    <h3>15 municipios de maior risco (dado oficial nomeado, INEP)</h3>
    __TABELA_MUNICIPIO_REAL__
  </div>
</div>

<script>
function mudarAba(evento, idAba) {
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.nav-button').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(idAba).classList.add('active');
    evento.currentTarget.classList.add('active');
}
</script>

</body>
</html>
"""


def valor_ou_nd(v: float, casas: int = 4) -> str:
    return f"{v:.{casas}f}" if v == v else "N/D"


tabela_metricas_df = pd.DataFrame({
    "Metrica": ["ROC AUC (teste)", "ROC AUC (validacao cruzada, media)", "F1 (validacao cruzada, media)"],
    "Valor": [
        valor_ou_nd(kpi_roc_auc),
        valor_ou_nd(kpi_roc_auc_cv),
        valor_ou_nd(kpi_f1_cv),
    ],
})
tabela_metricas_html = tabela_html(tabela_metricas_df)

html_final = (
    HTML_TEMPLATE
    .replace("__TOTAL_ALUNOS__", f"{kpi_total_alunos:,}")
    .replace("__TAXA_ALFABETIZACAO__", f"{kpi_taxa_alfabetizacao:.1%}")
    .replace("__ESCOLAS__", f"{kpi_escolas:,}")
    .replace("__UFS__", str(kpi_ufs))
    .replace("__ROC_AUC__", valor_ou_nd(kpi_roc_auc, 3))
    .replace("__TABELA_METRICAS__", tabela_metricas_html)
    .replace("__IMG_DISTRIBUICAO_RISCO__", img_distribuicao_risco)
    .replace("__IMG_RISCO_UF__", img_risco_uf)
    .replace("__IMG_FEATURE_IMPORTANCE__", img_feature_importance)
    .replace("__IMG_SHAP__", img_shap)
    .replace("__TABELA_RISCO_UF__", tabela_risco_uf_html)
    .replace("__TABELA_MUNICIPIO_REAL__", tabela_municipio_real_html)
    .replace("__TABELA_PIORES_ESCOLAS__", piores_escolas_html)
    .replace("__TABELA_MELHORES_ESCOLAS__", melhores_escolas_html)
)

print(f"Dashboard montado: {len(html_final):,} caracteres.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Publica no Volume e exibe

# COMMAND ----------

CAMINHO_DASHBOARD = "/Volumes/workspace/gold/dashboard/fase3_command_center.html"

try:
    with open(CAMINHO_DASHBOARD, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"Dashboard salvo em: {CAMINHO_DASHBOARD}")
except Exception as exc:
    print(f"Nao foi possivel salvar no Volume ({exc}). Exibindo mesmo assim.")

displayHTML(html_final)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Retorno para o pipeline runner (se houver)

# COMMAND ----------

dbutils.notebook.exit(
    f"Dashboard Fase 3 publicado: {kpi_total_alunos:,} alunos, ROC AUC teste = {kpi_roc_auc:.4f}"
)