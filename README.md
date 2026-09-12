# Tech Challenge Fase 3

Projeto de análise de dados educacionais sobre alfabetização infantil. O trabalho combina dados oficiais, dimensões territoriais e microdados de alunos para identificar padrões associados às diferenças de desempenho e apoiar decisões estratégicas.

## Sumário

- [Visão geral](#visão-geral)
- [Fase 0 - Dados e preparação](#fase-0---dados-e-preparação)
- [Fase 1 - Enriquecimento](#fase-1---enriquecimento)
- [Fase 2 - Análise exploratória](#fase-2---análise-exploratória)
- [Fase 3 - Modelagem](#fase-3---modelagem)
- [Fase 4 - Interpretabilidade](#fase-4---interpretabilidade)
- [Fase 5 - Aplicação estratégica](#fase-5---aplicação-estratégica)
- [Principais achados](#principais-achados)
- [Limitações e próximos passos](#limitações-e-próximos-passos)

## Visão geral

A pergunta central do projeto é:

> Quais fatores observáveis estão associados às diferenças nas taxas de alfabetização infantil?

A análise foi conduzida progressivamente, do contexto agregado ao indivíduo:

```text
Dados oficiais -> território -> rede de ensino -> escola -> aluno -> decisão estratégica
```

O objetivo é identificar associações e padrões úteis para diagnóstico. Os resultados não devem ser interpretados como evidência de causalidade.

## Fase 0 - Dados e preparação

As fontes principais são INEP, IBGE e os microdados `TS_ALUNO.csv` da Avaliação da Alfabetização (Saeb) 2023.

As tabelas analíticas da camada Gold utilizadas no projeto são:

- `indicador_municipio`
- `resumo_uf`
- `meta_vs_resultado`
- `evolucao_temporal`
- `base_modelagem_aluno`

No nível agregado, `taxa_alfabetizacao_media` representa a taxa oficial da fonte. No nível individual, o projeto utiliza o ponto de corte de 743 pontos de proficiência, representado pelo target `alfabetizado_oficial`.

A proficiência não é utilizada como feature da modelagem, evitando vazamento de informação (`data leakage`).

### Dados e versionamento

Não versionar a base oficial neste diretório. Registrar o procedimento de acesso ou exportação da tabela `gold.base_modelagem_aluno`, incluindo data, volume, schema e validações executadas.

## Fase 1 - Enriquecimento

O enriquecimento integra indicadores educacionais, território, metas, evolução temporal e informações no grão do aluno. A construção deve preservar:

- o grão original de cada fonte;
- a rastreabilidade dos de-para de rede e território;
- a proveniência dos indicadores;
- a separação entre dados observados e variáveis derivadas;
- a prevenção de vazamento do target.

O script principal desta etapa é [`00_enriquecimento_fundeb.py`](notebooks/00_enriquecimento_fundeb.py).

## Fase 2 - Análise exploratória

O script [`01_eda.py`](notebooks/01_eda.py) investiga os dados do território ao aluno.

### Visão municipal

Na amostra da EDA foram observados:

- 10.000 registros;
- 5.339 municípios;
- 25 UFs;
- 2 anos;
- taxa mínima de 4,4%;
- média de 61,8%;
- taxa máxima de 100%.

A dispersão municipal é ampla: há municípios próximos de 100% e municípios abaixo de 10%.

### Hipótese 1 - O território está associado ao desempenho?

As médias regionais foram aproximadamente:

| Região | Taxa média |
| --- | ---: |
| Sudeste | 63,94% |
| Sul | 62,28% |
| Centro-Oeste | 59,12% |
| Nordeste | 53,01% |
| Norte | 51,71% |

A hipótese foi parcialmente confirmada. Existem diferenças entre regiões e UFs, mas também grande desigualdade entre municípios da mesma UF.

### Hipótese 2 - A rede de ensino explica as diferenças?

Na análise agregada, as médias foram aproximadamente 59,06% na rede estadual, 55,46% na privada e 55,19% na municipal. Porém, o cruzamento rede x UF não apresentou padrão consistente.

A hipótese de uma rede superior em todos os contextos não foi confirmada. A associação depende fortemente do território.

### Hipótese 3 - Capitais apresentam melhores resultados?

| Ano | Capital | Interior |
| --- | ---: | ---: |
| 2023 | 53,35% | 60,59% |
| 2024 | 55,08% | 63,07% |

O interior apresentou média superior nos dois anos. A hipótese de vantagem automática das capitais não foi confirmada. Esse resultado é associativo, não causal.

### Análise no nível do aluno

Na `base_modelagem_aluno` foram observados 7.309 alunos, 7.309 IDs únicos, 5 UFs e 2 categorias de rede.

| Classificação | Alunos | Percentual |
| --- | ---: | ---: |
| Não alfabetizado | 4.697 | 64,26% |
| Alfabetizado | 2.612 | 35,74% |

Todos os alunos tinham `serie = 2`; portanto, não há variação suficiente para avaliar o efeito da série.

### Hipótese 4 - A participação na avaliação está associada à alfabetização?

Todos os alunos classificados como alfabetizados estavam no grupo com presença e preenchimento válidos. Entre os alunos com `presenca_lp = 1` e `preenchimento_lp = 1`, a taxa foi de aproximadamente 46,08%; entre os demais, não houve alfabetizados.

Essa é uma associação muito forte, mas as variáveis estão diretamente relacionadas ao processo que mede o resultado. Por isso, devem ser avaliadas com cuidado antes da modelagem e não podem ser interpretadas como causa.

### Hipótese 5 - A escola está associada ao resultado?

A base contém 220 escolas. Considerando apenas alunos presentes, com preenchimento válido, e escolas com pelo menos 10 alunos avaliados, as taxas variaram de 0% a 96,55%.

Exemplos de maiores taxas:

| Escola | Avaliados | Alfabetizados | Taxa |
| --- | ---: | ---: | ---: |
| 61420784 | 29 | 28 | 96,55% |
| 61400948 | 22 | 21 | 95,45% |
| 61437798 | 34 | 31 | 91,18% |
| 61428332 | 18 | 16 | 88,89% |

Também foram encontradas escolas com 0% entre alunos efetivamente avaliados. A hipótese foi fortemente sustentada como associação observável, sem implicar causalidade isolada da escola.

### Hipótese 6 - A diferença territorial permanece entre alunos avaliados?

Mesmo restringindo a análise a `presenca_lp = 1` e `preenchimento_lp = 1`, as taxas por UF variaram de 31,69% no Pará a 57,66% em Rondônia.

As diferenças territoriais permanecem, portanto, não são explicadas apenas pela participação na avaliação.

### Metas e evolução temporal

`meta_vs_resultado` apresentou inconsistências de preenchimento em `meta_taxa`, `gap_meta`, `atingiu_meta` e `atingiu_meta_brasil`. Por isso, essa tabela não foi utilizada como evidência central até que o grão e os campos sejam validados.

Em `evolucao_temporal`, a média agregada passou aproximadamente de 59,89% em 2023 para 62,17% em 2024. Como a tabela combina níveis territoriais e redes, esse resultado é tratado apenas como evidência exploratória.

## Fase 3 - Modelagem

O script [`02_modelagem.py`](notebooks/02_modelagem.py) utiliza a `base_modelagem_aluno` para treino, tuning, validação e comparação de modelos de classificação.

Cuidados essenciais:

- manter `alfabetizado_oficial` como target;
- excluir proficiência e variáveis derivadas diretamente dela;
- avaliar o desbalanceamento do target;
- separar treino e teste sem vazamento;
- comparar métricas além da acurácia;
- documentar decisões e limitações do modelo.

## Fase 4 - Interpretabilidade

O script [`03_interpretabilidade.py`](notebooks/03_interpretabilidade.py) analisa importância de variáveis, explicações locais e globais e, quando aplicável, SHAP.

As explicações devem ser lidas como associações do modelo. Elas não transformam correlação em causalidade e não substituem validação estatística ou conhecimento do domínio.

## Fase 5 - Aplicação estratégica

O script [`04_aplicacao_estrategica.py`](notebooks/04_aplicacao_estrategica.py) transforma os achados em riscos, prioridades e respostas para apoiar decisões educacionais.

O foco estratégico é localizar contextos de maior desigualdade, priorizar investigação e direcionar recursos. Nenhuma recomendação deve tratar uma variável isolada como causa suficiente do desempenho.

## Principais achados

- A desigualdade aparece entre regiões, entre UFs, dentro das UFs, entre municípios, entre escolas e entre alunos.
- O território está associado ao desempenho, mas não explica sozinho toda a variação.
- Nenhuma rede de ensino apresentou superioridade consistente em todas as UFs.
- As capitais não apresentaram vantagem média na amostra analisada.
- Participação e preenchimento da avaliação têm associação muito forte com o target e exigem cuidado por possível atalho de mensuração.
- A escola foi uma das associações mais fortes: entre alunos efetivamente avaliados, as taxas variaram de 0% a 96,55%.
- As diferenças entre UFs persistiram mesmo após controlar presença e preenchimento.

### Diagnóstico

Os resultados indicam que escola, participação do aluno e contexto territorial são os principais fatores observáveis associados às diferenças identificadas. A desigualdade é multifatorial e não deve ser atribuída a uma única característica.

## Limitações e próximos passos

A base atual não representa suficientemente variáveis como renda familiar, escolaridade dos responsáveis, infraestrutura escolar, formação docente, gestão e políticas públicas. Essas dimensões são hipóteses para uma próxima etapa, não causas demonstradas por esta EDA.

No nível individual, `id_municipio` é anonimizado e não deve ser cruzado diretamente com a dimensão territorial do IBGE. A UF é a geografia confiável para essa análise; `capital` e `nome_municipio` não estavam preenchidos na amostra.

Próximos passos sugeridos:

1. Validar o preenchimento e o grão de `meta_vs_resultado`.
2. Enriquecer a base com indicadores socioeconômicos, infraestrutura e contexto escolar.
3. Treinar e validar modelos supervisionados com controle rigoroso de vazamento.
4. Interpretar os modelos junto às evidências da EDA e às restrições do domínio.
5. Transformar os resultados validados em prioridades de acompanhamento e intervenção.

## Estrutura

```text
notebooks/
	00_enriquecimento_fundeb.py
	01_eda.py
	02_modelagem.py
	03_interpretabilidade.py
	04_aplicacao_estrategica.py
data/       # fontes e documentação de acesso
queries/    # consultas SQL
src/        # módulos reutilizáveis
reports/    # relatórios
```
