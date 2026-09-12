# Databricks notebook source
# MAGIC %md
# MAGIC # 00: Enriquecimento com dados do FUNDEB
# MAGIC
# MAGIC Limpa as 3 tabelas de instituicoes do FUNDEB que estao prontas
# MAGIC (`data/ENRIQUECIMENTO_E_FEATURES.md` marca as demais como upload
# MAGIC pendente), agrega por UF, e junta na base de aluno.
# MAGIC
# MAGIC **Por que agregado por UF, e nao por municipio**: o `01_eda.py`
# MAGIC (secao 14) ja documentou que `id_municipio` na base de aluno e
# MAGIC anonimizado e nao corresponde ao codigo real do IBGE. As tabelas do
# MAGIC FUNDEB usam nome de municipio real. Juntar por municipio produziria
# MAGIC um cruzamento incorreto, silenciosamente. `sigla_uf` e o unico nivel
# MAGIC territorial confiavel para o aluno, entao o enriquecimento fica nesse
# MAGIC grao.
# MAGIC
# MAGIC **PNAD nao entra aqui**: o arquivo disponivel e um dicionario de
# MAGIC variaveis (metadado), nao dados numericos, e a fonte original e de
# MAGIC 1997. Ver secao 5 para o registro completo dessa decisao.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------
import glob

import pandas as pd

CATALOG = "workspace"
DATA_DIR = "../data"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Leitura e limpeza das 3 tabelas de instituicoes
# MAGIC
# MAGIC As 3 estao prontas segundo `ENRIQUECIMENTO_E_FEATURES.md`
# MAGIC (conveniadas, AEE, educacao profissional). As demais tabelas do
# MAGIC FUNDEB (educacao infantil, VAAT, VAAR) estao marcadas como upload
# MAGIC pendente e nao sao usadas aqui.
# MAGIC
# MAGIC Cada arquivo tem uma peculiaridade de cabecalho diferente, tratada
# MAGIC individualmente abaixo em vez de um loop generico, para deixar
# MAGIC explicito o que cada leitura está pulando e por que.

# COMMAND ----------
conveniadas = pd.read_csv(
    f"{DATA_DIR}/InstituicoesConveniadasFundeb2026(conveniadas).csv",
    encoding="latin1",
    sep=";",
    header=1,
)
conveniadas.columns = conveniadas.columns.str.strip()
print(f"conveniadas: {len(conveniadas):,} linhas, colunas: {list(conveniadas.columns)}")

# COMMAND ----------
caminho_aee = f"{DATA_DIR}/InstituiesdeAEEFundeb2026Revisada(Consulta Escolas - Oferecem AEE).csv"
aee = pd.read_csv(caminho_aee, encoding="latin1", sep=";", header=1)
aee.columns = aee.columns.str.strip()
print(f"aee: {len(aee):,} linhas, colunas: {list(aee.columns)}")

# COMMAND ----------
# Nome do arquivo tem acentos mal codificados no repositorio; glob evita
# depender de digitar o nome exato.
caminho_prof = glob.glob(f"{DATA_DIR}/*Profissional*.csv")[0]
profissional = pd.read_csv(caminho_prof, encoding="latin1", sep=";", header=2)
profissional.columns = profissional.columns.str.strip()
print(f"profissional: {len(profissional):,} linhas, colunas: {list(profissional.columns)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Agregacao por UF
# MAGIC
# MAGIC Para cada fonte: quantidade de instituicoes e total de alunos
# MAGIC atendidos por UF. Colunas de "numero de alunos" vem como texto com
# MAGIC virgula decimal em pelo menos uma fonte, tratado explicitamente.

# COMMAND ----------
def para_numero(coluna: pd.Series) -> pd.Series:
    """Converte coluna que pode vir como texto com virgula decimal ou NaN."""
    if coluna.dtype == object:
        coluna = coluna.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(coluna, errors="coerce")

# COMMAND ----------
agg_conveniadas = (
    conveniadas.groupby("UF")
    .agg(
        instituicoes_conveniadas=("Entidade", "count"),
        alunos_conveniadas=("Número de Alunos", lambda s: para_numero(s).sum()),
    )
    .reset_index()
)

agg_aee = (
    aee.groupby("UF")
    .agg(
        instituicoes_aee=("Entidade", "count"),
        alunos_aee=("Alunos Contemplados", lambda s: para_numero(s).sum()),
    )
    .reset_index()
)

agg_profissional = (
    profissional.groupby("UF")
    .agg(
        instituicoes_profissional=("Entidade", "count"),
        alunos_profissional=("Número de Alunos", lambda s: para_numero(s).sum()),
    )
    .reset_index()
)

enriquecimento_uf = (
    agg_conveniadas.merge(agg_aee, on="UF", how="outer")
    .merge(agg_profissional, on="UF", how="outer")
    .rename(columns={"UF": "sigla_uf"})
    .fillna(0)
)

print(f"UFs cobertas: {len(enriquecimento_uf)}")
enriquecimento_uf

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Publicacao como tabela Gold
# MAGIC
# MAGIC Publica o enriquecimento como tabela propria, para o `02_modelagem`
# MAGIC consumir via join, em vez de recalcular a limpeza dos CSVs a cada
# MAGIC execucao.

# COMMAND ----------
spark.createDataFrame(enriquecimento_uf).write.mode("overwrite").saveAsTable(
    f"{CATALOG}.gold.enriquecimento_fundeb_uf"
)
print(f"Publicado em {CATALOG}.gold.enriquecimento_fundeb_uf")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Junta na base de aluno e valida cobertura

# COMMAND ----------
base_aluno = spark.sql(f"SELECT * FROM {CATALOG}.gold.base_modelagem_aluno").toPandas()

base_enriquecida = base_aluno.merge(enriquecimento_uf, on="sigla_uf", how="left")

cobertura = base_enriquecida["instituicoes_conveniadas"].notna().mean()
print(f"Cobertura do enriquecimento na base de aluno: {cobertura:.1%}")

if cobertura < 1.0:
    ufs_sem_match = sorted(
        set(base_aluno["sigla_uf"].unique()) - set(enriquecimento_uf["sigla_uf"].unique())
    )
    print(f"UFs da base de aluno sem correspondencia no FUNDEB: {ufs_sem_match}")

# COMMAND ----------
spark.createDataFrame(base_enriquecida).write.mode("overwrite").saveAsTable(
    f"{CATALOG}.gold.base_modelagem_aluno_enriquecida"
)
print(f"Publicado em {CATALOG}.gold.base_modelagem_aluno_enriquecida")
print(f"Colunas novas: instituicoes_conveniadas, alunos_conveniadas, instituicoes_aee, alunos_aee, instituicoes_profissional, alunos_profissional")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Fontes avaliadas e descartadas nesta etapa
# MAGIC
# MAGIC Registro explicito do que foi considerado e por que nao entrou,
# MAGIC para nao repetir a investigacao depois:
# MAGIC
# MAGIC - **PNAD** (`PNAD_ajuste_variaveis_e_analise_metricas...csv`): o
# MAGIC   arquivo disponivel e um dicionario de variaveis (nomes de
# MAGIC   categorias e metricas), nao a base de dados numerica em si. Alem
# MAGIC   disso a fonte e de 1997, quase 30 anos anterior aos dados de
# MAGIC   2023/2024 usados no restante do projeto. Nao foi enriquecido.
# MAGIC - **FUNDEB educacao infantil, VAAT, VAAR**: marcados como upload
# MAGIC   pendente em `ENRIQUECIMENTO_E_FEATURES.md`. Se esses arquivos
# MAGIC   forem obtidos, o padrao de limpeza e agregacao deste notebook
# MAGIC   (leitura com o header correto, conversao de numero com virgula
# MAGIC   decimal, agregacao por UF) se aplica da mesma forma.
# MAGIC - **Censo Escolar dicionario**: e um dicionario de codigos (chave,
# MAGIC   valor), util para interpretar colunas do Bronze, mas nao e uma
# MAGIC   fonte numerica para juntar como feature.
# MAGIC - **feature_store da Fase 2** (37 features, grao UF/ano, tabela
# MAGIC   `alfabetizacao_feature_store`): joinavel por `sigla_uf` + `ano`
# MAGIC   se essa tabela existir no workspace. Nao incluido neste notebook
# MAGIC   porque a tabela vive em outro catalogo/schema dependendo de onde
# MAGIC   foi criada; confirmar o caminho exato antes de adicionar esse
# MAGIC   join.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Retorno para o pipeline runner (se houver)

# COMMAND ----------
dbutils.notebook.exit(
    f"Enriquecimento FUNDEB publicado: {len(enriquecimento_uf)} UFs, "
    f"cobertura na base de aluno = {cobertura:.1%}"
)
