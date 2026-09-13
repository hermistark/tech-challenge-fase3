# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # 01: Analise Exploratoria de Dados - Alfabetizacao Infantil
# MAGIC
# MAGIC Pergunta principal: **quais fatores observaveis estao associados as
# MAGIC diferencas nas taxas de alfabetizacao infantil?**
# MAGIC
# MAGIC A investigacao percorre o territorio ate o nivel individual do aluno:
# MAGIC
# MAGIC ```text
# MAGIC Territorio -> Rede de ensino -> Contexto municipal -> Participacao do
# MAGIC aluno -> Escola -> Territorio no nivel do aluno
# MAGIC ```
# MAGIC
# MAGIC O objetivo nao e demonstrar causalidade, e sim identificar padroes e
# MAGIC associacoes fortes o suficiente para orientar a modelagem da Fase 3.
# MAGIC
# MAGIC Fontes: marts da Gold construidos na Fase 2 (`indicador_municipio`,
# MAGIC `resumo_uf`, `meta_vs_resultado`, `evolucao_temporal`,
# MAGIC `base_modelagem_aluno`).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Setup

# COMMAND ----------

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

CATALOG = "workspace"
sns.set_style("whitegrid")


def rodar(query: str) -> pd.DataFrame:
    """Executa uma query Spark SQL e devolve pandas, para plot e leitura rapida."""
    return spark.sql(query).toPandas()


spark.sql(f"USE CATALOG {CATALOG}")
spark.sql("USE SCHEMA gold")
print("Catalogo e schema configurados: workspace.gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Visao geral dos indicadores municipais
# MAGIC
# MAGIC Ponto de partida: distribuicao geral das taxas em `indicador_municipio`.

# COMMAND ----------

visao_geral = rodar("""
    SELECT
        COUNT(*) AS total_registros,
        COUNT(DISTINCT id_municipio) AS municipios,
        COUNT(DISTINCT sigla_uf) AS ufs,
        COUNT(DISTINCT ano) AS anos,
        MIN(taxa_alfabetizacao_media) AS menor_taxa,
        AVG(taxa_alfabetizacao_media) AS taxa_media,
        MAX(taxa_alfabetizacao_media) AS maior_taxa
    FROM indicador_municipio
""")
visao_geral

# COMMAND ----------

faixas = rodar("""
    SELECT
        CASE
            WHEN taxa_alfabetizacao_media < 0.50 THEN '0-49%'
            WHEN taxa_alfabetizacao_media < 0.60 THEN '50-59%'
            WHEN taxa_alfabetizacao_media < 0.70 THEN '60-69%'
            WHEN taxa_alfabetizacao_media < 0.80 THEN '70-79%'
            WHEN taxa_alfabetizacao_media < 0.90 THEN '80-89%'
            ELSE '90-100%'
        END AS faixa,
        COUNT(*) AS quantidade
    FROM indicador_municipio
    GROUP BY
        CASE
            WHEN taxa_alfabetizacao_media < 0.50 THEN '0-49%'
            WHEN taxa_alfabetizacao_media < 0.60 THEN '50-59%'
            WHEN taxa_alfabetizacao_media < 0.70 THEN '60-69%'
            WHEN taxa_alfabetizacao_media < 0.80 THEN '70-79%'
            WHEN taxa_alfabetizacao_media < 0.90 THEN '80-89%'
            ELSE '90-100%'
        END
    ORDER BY MIN(taxa_alfabetizacao_media)
""")

fig, ax = plt.subplots(figsize=(8, 4))
sns.barplot(data=faixas, x="faixa", y="quantidade", ax=ax, color="#4C72B0")
ax.set_title("Distribuicao dos municipios por faixa de taxa de alfabetizacao")
ax.set_xlabel("Faixa")
ax.set_ylabel("Municipios")
plt.tight_layout()
plt.show()

print(
    "Ha uma dispersao muito grande entre os resultados municipais. "
    "Hipotese 1: o territorio explica as diferencas de alfabetizacao?"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Hipotese 1: o territorio esta associado ao desempenho?

# COMMAND ----------

regiao = rodar("""
    SELECT regiao, AVG(taxa_alfabetizacao_media) AS taxa_media
    FROM resumo_uf
    WHERE rede_label <> 'total'
    GROUP BY regiao
    ORDER BY taxa_media DESC
""")

fig, ax = plt.subplots(figsize=(8, 4))
sns.barplot(data=regiao, x="regiao", y="taxa_media", ax=ax, color="#55A868")
ax.set_title("Taxa media de alfabetizacao por regiao")
plt.tight_layout()
plt.show()

# COMMAND ----------

dispersao_uf = rodar("""
    WITH medias AS (
        SELECT sigla_uf, nome_uf, AVG(taxa_alfabetizacao_media) AS media
        FROM indicador_municipio
        GROUP BY sigla_uf, nome_uf
    ),
    estatisticas AS (
        SELECT
            i.sigla_uf,
            i.nome_uf,
            AVG(i.taxa_alfabetizacao_media) AS media,
            MIN(i.taxa_alfabetizacao_media) AS menor,
            MAX(i.taxa_alfabetizacao_media) AS maior,
            sqrt(
                AVG(
                    (i.taxa_alfabetizacao_media - m.media) *
                    (i.taxa_alfabetizacao_media - m.media)
                )
            ) AS desvio_padrao
        FROM indicador_municipio i
        JOIN medias m ON i.sigla_uf = m.sigla_uf
        GROUP BY i.sigla_uf, i.nome_uf
    )
    SELECT
        sigla_uf, nome_uf, media, menor, maior, desvio_padrao,
        maior - menor AS amplitude
    FROM estatisticas
    ORDER BY amplitude DESC
""")
dispersao_uf.head(10)

# COMMAND ----------

print(
    "Conclusao (hipotese 1): PARCIALMENTE CONFIRMADA. O territorio esta "
    "fortemente associado ao desempenho, mas regiao ou UF isoladamente nao "
    "explicam toda a desigualdade. A desigualdade existe entre estados e "
    "tambem dentro deles (ver coluna amplitude acima)."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Hipotese 2: a rede de ensino explica as diferencas?

# COMMAND ----------

rede_geral = rodar("""
    SELECT rede_label, COUNT(*) AS registros, AVG(taxa_alfabetizacao_media) AS taxa_media,
           MIN(taxa_alfabetizacao_media) AS menor_taxa, MAX(taxa_alfabetizacao_media) AS maior_taxa
    FROM resumo_uf
    GROUP BY rede_label
    ORDER BY taxa_media DESC
""")
rede_geral

# COMMAND ----------

rede_por_uf = rodar("""
    SELECT sigla_uf, nome_uf, regiao, rede_label, AVG(taxa_alfabetizacao_media) AS media
    FROM resumo_uf
    WHERE rede_label <> 'total'
    GROUP BY sigla_uf, nome_uf, regiao, rede_label
    ORDER BY sigla_uf, media DESC
""")

for uf in ["RJ", "CE", "PR"]:
    print(f"\n{uf}:")
    print(rede_por_uf[rede_por_uf["sigla_uf"] == uf].to_string(index=False))

print(
    "\nConclusao (hipotese 2): NAO CONFIRMADA. A rede que aparece na frente "
    "muda de UF para UF. Nao ha rede consistentemente superior em todos os "
    "estados analisados."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Hipotese 3: capitais apresentam melhores resultados?

# COMMAND ----------

capitais = [
    "Rio Branco", "Maceio", "Macapa", "Manaus", "Salvador", "Fortaleza",
    "Brasilia", "Vitoria", "Goiania", "Sao Luis", "Cuiaba", "Campo Grande",
    "Belo Horizonte", "Belem", "Joao Pessoa", "Curitiba", "Recife",
    "Teresina", "Rio de Janeiro", "Natal", "Porto Alegre", "Porto Velho",
    "Boa Vista", "Florianopolis", "Sao Paulo", "Aracaju", "Palmas",
]
capitais_sql = ", ".join(f"'{c}'" for c in capitais)

capital_interior_ano = rodar(f"""
    SELECT
        ano,
        CASE WHEN nome_municipio IN ({capitais_sql}) THEN 'Capital' ELSE 'Interior' END AS tipo_municipio,
        COUNT(*) AS registros,
        AVG(taxa_alfabetizacao_media) AS taxa_media
    FROM indicador_municipio
    GROUP BY ano, CASE WHEN nome_municipio IN ({capitais_sql}) THEN 'Capital' ELSE 'Interior' END
    ORDER BY ano, tipo_municipio
""")

fig, ax = plt.subplots(figsize=(7, 4))
sns.barplot(data=capital_interior_ano, x="ano", y="taxa_media", hue="tipo_municipio", ax=ax)
ax.set_title("Capital x interior, por ano")
plt.tight_layout()
plt.show()

print(
    "Conclusao (hipotese 3): NAO CONFIRMADA. O interior apresentou "
    "desempenho medio superior nos anos analisados. Nao houve vantagem "
    "automatica das capitais na amostra."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Nivel do aluno: visao geral de `base_modelagem_aluno`
# MAGIC
# MAGIC A partir daqui descemos para o menor grao disponivel: o aluno. Essa e a
# MAGIC base que sera usada na modelagem supervisionada (`02_modelagem`).

# COMMAND ----------

base_geral = rodar("""
    SELECT
        COUNT(*) AS total_registros,
        COUNT(DISTINCT id_aluno) AS alunos_unicos,
        COUNT(DISTINCT sigla_uf) AS ufs,
        COUNT(DISTINCT rede_label) AS redes
    FROM base_modelagem_aluno
""")
base_geral

# COMMAND ----------

# MAGIC %md
# MAGIC ### Desbalanceamento do target `alfabetizado_oficial`
# MAGIC
# MAGIC Item do checklist do edital: avaliar desbalanceamento antes de escolher
# MAGIC metrica de modelagem (accuracy pode enganar num cenario desbalanceado).

# COMMAND ----------

target_balance = rodar("""
    SELECT
        alfabetizado_oficial,
        COUNT(*) AS alunos,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM base_modelagem_aluno WHERE alfabetizado_oficial IS NOT NULL), 2) AS percentual
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL
    GROUP BY alfabetizado_oficial
    ORDER BY alfabetizado_oficial
""")

fig, ax = plt.subplots(figsize=(5, 4))
sns.barplot(data=target_balance, x="alfabetizado_oficial", y="alunos", ax=ax, color="#C44E52")
ax.set_title("Balanceamento do target: alfabetizado_oficial")
plt.tight_layout()
plt.show()

print(target_balance.to_string(index=False))
print(
    "\nO target esta desbalanceado (nao e 50/50). Isso deve orientar a "
    "escolha de metrica na Fase 3: preferir F1, AUC e recall por classe em "
    "vez de accuracy pura, e considerar estratificacao no split treino/teste."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Serie escolar

# COMMAND ----------

serie = rodar("""
    SELECT serie, COUNT(*) AS alunos,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL
    GROUP BY serie
    ORDER BY serie
""")
serie

# COMMAND ----------

if serie["serie"].nunique() <= 1:
    print(
        "A serie nao varia nesta amostra (100% na mesma serie). Nao pode "
        "ser usada para explicar diferencas de alfabetizacao, e candidata a "
        "ser descartada como feature por ausencia de variancia."
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Hipotese 4: participacao na avaliacao esta associada a alfabetizacao?
# MAGIC
# MAGIC Atencao: `presenca_lp` e `preenchimento_lp` sao candidatas fortes a
# MAGIC vazamento indireto (estao ligadas ao proprio processo de mensuracao do
# MAGIC target). Avaliar com cuidado antes de usar como feature na modelagem.

# COMMAND ----------

presenca = rodar("""
    SELECT presenca_lp, COUNT(*) AS alunos,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           SUM(CASE WHEN alfabetizado_oficial = 0 THEN 1 ELSE 0 END) AS nao_alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL
    GROUP BY presenca_lp
    ORDER BY presenca_lp
""")
presenca

# COMMAND ----------

presenca_preenchimento = rodar("""
    SELECT preenchimento_lp, presenca_lp, COUNT(*) AS alunos,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           SUM(CASE WHEN alfabetizado_oficial = 0 THEN 1 ELSE 0 END) AS nao_alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL
    GROUP BY preenchimento_lp, presenca_lp
    ORDER BY preenchimento_lp, presenca_lp
""")
presenca_preenchimento

# COMMAND ----------

print(
    "Associacao muito forte entre participacao valida e alfabetizacao. "
    "IMPORTANTE para a modelagem: presenca_lp e preenchimento_lp funcionam "
    "quase como um atalho para o target (todo aluno alfabetizado esta no "
    "grupo presente+preenchido). Avaliar exclusao ou tratamento especial "
    "dessas colunas no notebook de preprocessamento para nao inflar "
    "artificialmente a performance do modelo."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Dependencia administrativa no nivel do aluno

# COMMAND ----------

dependencia = rodar("""
    SELECT tp_dependencia, rede, rede_label, COUNT(*) AS alunos,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           SUM(CASE WHEN alfabetizado_oficial = 0 THEN 1 ELSE 0 END) AS nao_alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL
    GROUP BY tp_dependencia, rede, rede_label
    ORDER BY taxa_alfabetizacao DESC
""")
dependencia

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Hipotese 5: a escola esta associada ao resultado?
# MAGIC
# MAGIC Uma das analises mais importantes: comparamos escolas controlando por
# MAGIC presenca e preenchimento validos, para nao confundir desempenho escolar
# MAGIC com ausencia na avaliacao.

# COMMAND ----------

escolas_geral = rodar("""
    SELECT COUNT(*) AS alunos, COUNT(DISTINCT id_escola) AS escolas
    FROM base_modelagem_aluno
    WHERE id_escola IS NOT NULL
""")
escolas_geral

# COMMAND ----------

melhores_escolas = rodar("""
    SELECT id_escola, COUNT(*) AS alunos_avaliados,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL AND presenca_lp = 1 AND preenchimento_lp = 1
    GROUP BY id_escola
    HAVING COUNT(*) >= 10
    ORDER BY taxa_alfabetizacao DESC
    LIMIT 15
""")

piores_escolas = rodar("""
    SELECT id_escola, COUNT(*) AS alunos_avaliados,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL AND presenca_lp = 1 AND preenchimento_lp = 1
    GROUP BY id_escola
    HAVING COUNT(*) >= 10
    ORDER BY taxa_alfabetizacao ASC
    LIMIT 15
""")

print("Melhores escolas (so alunos avaliados):")
print(melhores_escolas.head(5).to_string(index=False))
print("\nPiores escolas (so alunos avaliados):")
print(piores_escolas.head(5).to_string(index=False))

print(
    f"\nMesmo controlando presenca e preenchimento, a taxa varia de "
    f"{piores_escolas['taxa_alfabetizacao'].min():.2%} a "
    f"{melhores_escolas['taxa_alfabetizacao'].max():.2%} entre escolas com "
    "pelo menos 10 alunos avaliados. A diferenca nao se explica so pelo "
    "tamanho da amostra."
)
print(
    "\nConclusao (hipotese 5): FORTEMENTE SUSTENTADA. A escola e um dos "
    "principais fatores observaveis associados as diferencas de "
    "alfabetizacao. Candidata forte a feature (id_escola ou agregados por "
    "escola) na modelagem."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Hipotese 6: a diferenca territorial permanece so com alunos avaliados?

# COMMAND ----------

uf_avaliados = rodar("""
    SELECT sigla_uf, COUNT(*) AS alunos_avaliados,
           SUM(CASE WHEN alfabetizado_oficial = 1 THEN 1 ELSE 0 END) AS alfabetizados,
           AVG(alfabetizado_oficial) AS taxa_alfabetizacao
    FROM base_modelagem_aluno
    WHERE alfabetizado_oficial IS NOT NULL AND presenca_lp = 1 AND preenchimento_lp = 1
    GROUP BY sigla_uf
    ORDER BY taxa_alfabetizacao DESC
""")

fig, ax = plt.subplots(figsize=(7, 4))
sns.barplot(data=uf_avaliados, x="sigla_uf", y="taxa_alfabetizacao", ax=ax, color="#8172B2")
ax.set_title("Taxa de alfabetizacao por UF, so alunos avaliados")
plt.tight_layout()
plt.show()

amplitude = uf_avaliados["taxa_alfabetizacao"].max() - uf_avaliados["taxa_alfabetizacao"].min()
print(
    f"Amplitude entre UFs (so avaliados): {amplitude:.2%}. "
    "Conclusao (hipotese 6): SUSTENTADA. A diferenca territorial permanece "
    "mesmo depois de controlar participacao valida na avaliacao, sigla_uf "
    "e uma feature territorial relevante para a modelagem."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Metas educacionais (`meta_vs_resultado`)
# MAGIC
# MAGIC Nota de qualidade de dados: durante a EDA o time encontrou
# MAGIC inconsistencias nesta tabela (campos de meta nulos ou nao populados na
# MAGIC amostra). Por isso ela nao foi usada para sustentar o diagnostico final.

# COMMAND ----------

metas_geral = rodar("""
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN atingiu_meta = TRUE THEN 1 ELSE 0 END) AS atingiram_meta,
           SUM(CASE WHEN atingiu_meta = FALSE THEN 1 ELSE 0 END) AS nao_atingiram_meta
    FROM meta_vs_resultado
""")
metas_geral

# COMMAND ----------

if metas_geral["atingiram_meta"].iloc[0] == 0 and metas_geral["nao_atingiram_meta"].iloc[0] == 0:
    print(
        "Confirmado: atingiu_meta nao esta populado na amostra atual. "
        "Antes de usar meta_vs_resultado na Fase 3, validar o preenchimento "
        "desses campos na fonte."
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Evolucao temporal (`evolucao_temporal`)
# MAGIC
# MAGIC Tratada como evidencia exploratoria, nao como conclusao central: a
# MAGIC tabela combina niveis territoriais e redes diferentes.

# COMMAND ----------

evolucao = rodar("""
    SELECT ano, COUNT(*) AS registros, AVG(taxa_alfabetizacao_media) AS taxa_media,
           AVG(variacao_absoluta) AS variacao_media_absoluta
    FROM evolucao_temporal
    GROUP BY ano
    ORDER BY ano
""")
evolucao

# COMMAND ----------

tendencia = rodar("""
    SELECT ano, tendencia, COUNT(*) AS quantidade
    FROM evolucao_temporal
    GROUP BY ano, tendencia
    ORDER BY ano, quantidade DESC
""")
tendencia

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Diagnostico final e implicacoes para a modelagem (Fase 3)

# COMMAND ----------

print("""
DIAGNOSTICO: as desigualdades de alfabetizacao nao sao explicadas por um
unico fator. Escola, participacao regular do aluno na avaliacao e contexto
territorial estao fortemente associados aos resultados; rede de ensino e
condicao de capital, isoladamente, nao explicam o padrao observado.

IMPLICACOES PARA 02_modelagem:
1. Target desbalanceado -> usar F1/AUC/recall por classe, nao so accuracy;
   considerar split estratificado.
2. presenca_lp e preenchimento_lp sao vazamento indireto em potencial
   (associacao quase determinista com o target) -> avaliar exclusao ou
   tratamento especial, documentar a decisao explicitamente.
3. id_escola e sigla_uf sao fortes candidatas a feature (efeito escola e
   efeito territorial persistem mesmo controlando participacao).
4. serie nao varia nesta amostra -> descartar como feature.
5. meta_vs_resultado e evolucao_temporal tem problemas de qualidade/grao
   nesta amostra -> nao usar como feature sem validacao adicional.
6. Enriquecimento externo (FUNDEB, PNAD, Censo Escolar) documentado em
   data/ENRIQUECIMENTO_E_FEATURES.md e o proximo passo natural para
   capturar fatores socioeconomicos ainda nao representados na base.
""")