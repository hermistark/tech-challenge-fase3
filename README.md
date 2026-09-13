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
- [Dashboard executivo](#dashboard-executivo)
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

O script [`02_modelagem.py`](notebooks/02_modelagem.py) utiliza a `base_modelagem_aluno` (enriquecida com FUNDEB quando disponível) para treinar e validar um classificador que prevê `alfabetizado_oficial`.

### Escolha do algoritmo

`RandomForestClassifier`, com `class_weight="balanced"` (compensando o desbalanceamento observado na EDA) e `max_depth=15`. O limite de profundidade não é só ajuste de performance: sem ele, o `id_escola` (mais de mil categorias após o one-hot) gerava árvores muito grandes, o que travou o cálculo de SHAP na etapa de interpretabilidade. Limitar a profundidade resolveu isso e também reduz o risco de overfitting.

### Tratamento de vazamento e exclusões

Excluídas da modelagem, com justificativa registrada no próprio notebook:

- `presenca_lp` e `preenchimento_lp` - vazamento indireto: 100% dos alunos alfabetizados na amostra estão no grupo presença+preenchimento válidos, e 0% dos ausentes são alfabetizados. É um atalho de mensuração, não um fator explicativo.
- `serie` - sem variância na amostra (100% série 2).
- `id_municipio`, `nome_municipio`, `capital` - `id_municipio` no grão de aluno é anonimizado; qualquer coluna derivada desse join chega vazia ou não confiável.
- `record_id`, `id_aluno` - identificadores únicos, não features.
- `processed_at`, `schema_version`, `source`, `fonte_dados`, `uf_consistente` - metadado de execução do pipeline, não característica do aluno.
- `VL_PROFICIENCIA_LP` - já excluída na origem (Fase 2).

### Split e validação

Split de Pareto (80% treino / 20% teste), estratificado pelo target. Validação cruzada com `StratifiedKFold` (5 folds).

### Resultado

| Métrica | Valor |
| --- | ---: |
| ROC AUC (teste) | 0,7873 |
| ROC AUC (validação cruzada, média) | 0,7883 |
| F1 (validação cruzada, média) | 0,6697 |

A proximidade entre o ROC AUC de teste e o de validação cruzada indica que o modelo generaliza de forma estável, sem sinal de overfitting ao split específico escolhido.

## Fase 4 - Interpretabilidade

O script [`03_interpretabilidade.py`](notebooks/03_interpretabilidade.py) carrega o modelo já treinado (via MLflow) e calcula Feature Importance nativa do RandomForest e SHAP values (`TreeExplainer`, amostra de até 1.000 linhas por custo computacional).

As explicações devem ser lidas como associações do modelo, coerentes com o que a EDA já havia mostrado (efeito escola e efeito território persistindo mesmo controlando participação válida na avaliação). Elas não transformam correlação em causalidade e não substituem validação estatística ou conhecimento do domínio.

## Fase 5 - Aplicação estratégica

O script [`04_aplicacao_estrategica.py`](notebooks/04_aplicacao_estrategica.py) responde diretamente às perguntas de negócio do edital:

- **Municípios de maior risco**: usa `gold.indicador_municipio` (Fase 2, INEP), com nome de município real e taxa de alfabetização observada - não o `id_municipio` anonimizado do grão de aluno, que não permitiria identificar onde agir.
- **Regiões com padrões semelhantes**: agrupamento de UFs por faixa de risco previsto pelo modelo (tercis).
- **Municípios em risco de não atingir metas futuras**: cruza taxa atual baixa (bottom 25%, dado oficial) com tendência de queda em `evolucao_temporal`, também por município nomeado. `meta_vs_resultado` não é usada para essa validação por ter inconsistência de preenchimento identificada na EDA.
- **Fatores de maior impacto**: resumo executivo remetendo à Fase 4.

Nenhuma recomendação trata uma variável isolada como causa suficiente do desempenho.

## Dashboard executivo

O script [`05_dashboard.py`](notebooks/05_dashboard.py) consolida visão geral, modelo, interpretabilidade e aplicação estratégica em um painel HTML com abas, renderizado via `displayHTML` no Databricks. Não recalcula nada do zero - lê o modelo do MLflow e os mesmos dados dos notebooks anteriores. Inclui uma aba dedicada de escolas (maior e menor risco, cruzadas com UF, não com município, pelo mesmo motivo de anonimização).

## Principais achados

- A desigualdade aparece entre regiões, entre UFs, dentro das UFs, entre municípios, entre escolas e entre alunos.
- O território está associado ao desempenho, mas não explica sozinho toda a variação.
- Nenhuma rede de ensino apresentou superioridade consistente em todas as UFs.
- As capitais não apresentaram vantagem média na amostra analisada.
- Participação e preenchimento da avaliação têm associação muito forte com o target e exigem cuidado por possível atalho de mensuração.
- A escola foi uma das associações mais fortes: entre alunos efetivamente avaliados, as taxas variaram de 0% a 96,55%.
- As diferenças entre UFs persistiram mesmo após controlar presença e preenchimento.
- O modelo supervisionado (RandomForest) alcançou ROC AUC de 0,79 em teste e validação cruzada, com F1 de 0,67 - desempenho estável, sem sinal de overfitting.

### Diagnóstico

Os resultados indicam que escola, participação do aluno e contexto territorial são os principais fatores observáveis associados às diferenças identificadas. A desigualdade é multifatorial e não deve ser atribuída a uma única característica.

## Limitações e próximos passos

A base atual não representa suficientemente variáveis como renda familiar, escolaridade dos responsáveis, infraestrutura escolar, formação docente, gestão e políticas públicas. Essas dimensões são hipóteses para uma próxima etapa, não causas demonstradas por esta EDA.

No nível individual, `id_municipio` é anonimizado e não deve ser cruzado diretamente com a dimensão territorial do IBGE. A UF é a geografia confiável para essa análise; `capital` e `nome_municipio` não estavam preenchidos na amostra.

Próximos passos sugeridos:

1. Validar o preenchimento e o grão de `meta_vs_resultado` na fonte, para uso futuro como validação real (hoje é só proxy por tendência).
2. Completar o enriquecimento FUNDEB: 3 das 7 tabelas ainda estão com upload pendente (`data/ENRIQUECIMENTO_E_FEATURES.md`).
3. Incorporar indicadores socioeconômicos adicionais (Censo Escolar, PNAD atualizado) além do que já está mapeado.
4. Tuning de hiperparâmetro (`GridSearchCV`/`RandomizedSearchCV`) além da validação cruzada já feita.
5. Gravar o vídeo executivo e revisar o histórico de commits/PRs do repositório antes da entrega final.

## Estrutura

```text
notebooks/
	00_enriquecimento_fundeb.py
	01_eda.py
	02_modelagem.py
	03_interpretabilidade.py
	04_aplicacao_estrategica.py
	05_dashboard.py
data/       # fontes e documentação de acesso
queries/    # consultas SQL
src/        # módulos reutilizáveis
reports/    # relatórios
```
