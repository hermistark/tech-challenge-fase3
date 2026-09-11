# Análise Exploratória de Dados -Alfabetização Infantil

## 1.0 Objetivo

Após a construção do pipeline de dados, realizamos uma análise exploratória sobre as tabelas da camada Gold com o objetivo de responder uma pergunta principal:

> **Quais fatores observáveis estão associados às diferenças nas taxas de alfabetização infantil?**

O pipeline integra indicadores oficiais de alfabetização por município e UF, metas educacionais, dimensões territoriais e microdados de alunos. A camada Gold disponibiliza cinco marts analíticos: `indicador_municipio`, `resumo_uf`, `meta_vs_resultado`, `evolucao_temporal` e `base_modelagem_aluno`.

A análise foi conduzida como uma investigação, partindo do território e avançando progressivamente até o nível individual do aluno.

A lógica utilizada foi:

**Território -> Rede de ensino -> Contexto municipal -> Participação do aluno -> Escola -> Território no nível do aluno**

Nosso objetivo não foi demonstrar causalidade, mas identificar padrões e associações suficientemente fortes para construir um diagnóstico baseado nos dados disponíveis.

---

# 2. Considerações sobre os dados

Os indicadores utilizados são provenientes de fontes oficiais, principalmente INEP e IBGE. O projeto também utiliza os microdados `TS_ALUNO.csv` da Avaliação da Alfabetização (Saeb) 2023 para a análise no grão individual.

Existe uma distinção importante entre o indicador agregado e o dado individual.

No nível agregado, `taxa_alfabetizacao_media` já representa a taxa oficial disponibilizada pela fonte. Portanto, não aplicamos novamente o corte de proficiência sobre esse indicador.

No nível individual, o critério de alfabetização utilizado pelo projeto considera o ponto de corte de **743 pontos de proficiência**.

Na Gold de modelagem, esse resultado está representado pelo target:

```text
alfabetizado_oficial
```

A proficiência utilizada para produzir essa classificação não é disponibilizada como feature da base de modelagem justamente para evitar vazamento de informação (`data leakage`).

---

# 3. Visão geral dos indicadores municipais

Começamos analisando `indicador_municipio` para entender a distribuição geral das taxas.

Na amostra utilizada na EDA encontramos:

* 10.000 registros;
* 5.339 municípios distintos;
* 25 UFs;
* 2 anos;
* menor taxa observada: **4,4%**;
* média: **61,8%**;
* maior taxa: **100%**.

A distribuição encontrada foi:

| Faixa   | Registros |
| ------- | --------: |
| 0–49%   |     2.846 |
| 50–59%  |     1.691 |
| 60–69%  |     1.790 |
| 70–79%  |     1.711 |
| 80–89%  |     1.208 |
| 90–100% |       754 |

A primeira conclusão foi que existe uma dispersão muito grande entre os resultados municipais.

Alguns municípios apresentaram taxas próximas de 100%, enquanto outros ficaram abaixo de 10%.

Isso nos levou à primeira hipótese da investigação:

> **O território explica as diferenças de alfabetização?**

---

# 4. Hipótese 1 -O território está associado ao desempenho?

Para investigar essa hipótese, analisamos primeiro as médias regionais e estaduais e depois a dispersão dos municípios dentro de cada UF.

As médias regionais encontradas foram aproximadamente:

| Região       | Taxa média |
| ------------ | ---------: |
| Sudeste      |     63,94% |
| Sul          |     62,28% |
| Centro-Oeste |     59,12% |
| Nordeste     |     53,01% |
| Norte        |     51,71% |

Também encontramos diferenças relevantes entre UFs.

O Ceará, por exemplo, apareceu entre os estados com maior desempenho, enquanto outros estados apresentaram médias consideravelmente menores.

Entretanto, a descoberta mais importante apareceu quando analisamos a variação **dentro de cada estado**.

Alguns exemplos:

| UF |  Média | Mínimo | Máximo |     Desvio |
| -- | -----: | -----: | -----: | ---------: |
| CE | 90,08% | 55,60% |   100% |  9,55 p.p. |
| PI | 62,75% |  7,20% |   100% | 22,53 p.p. |
| RS | 62,97% |  4,40% |   100% | 17,68 p.p. |
| TO | 42,44% |  4,60% | 95,50% | 16,67 p.p. |

Isso mostrou que a desigualdade não ocorre somente entre estados.

**Dentro de uma mesma UF existem municípios com desempenhos muito diferentes.**

### Conclusão

A hipótese foi **parcialmente confirmada**.

O território está fortemente associado ao desempenho, mas região ou UF, isoladamente, não explicam toda a desigualdade.

> **A desigualdade existe entre estados e também dentro deles.**

---

# 5. Hipótese 2 -A rede de ensino explica as diferenças?

Depois da análise territorial, investigamos se a dependência administrativa poderia ser a principal explicação.

Na análise agregada encontramos aproximadamente:

| Rede      | Taxa média |
| --------- | ---------: |
| Estadual  |     59,06% |
| Privada   |     55,46% |
| Municipal |     55,19% |

À primeira vista, a rede estadual poderia parecer superior.

Entretanto, quando cruzamos **rede × UF**, o padrão deixou de ser consistente.

Alguns exemplos:

**Rio de Janeiro**

* Estadual: ~80,09%
* Privada: ~53,69%
* Municipal: ~53,68%

**Ceará**

* Municipal: ~84,92%
* Privada: ~84,89%
* Estadual: ~78,56%

**Paraná**

* Municipal: ~71,77%
* Privada: ~71,77%
* Estadual: ~71,15%

Em determinados estados a rede estadual aparece na frente. Em outros, a municipal apresenta resultado superior. Em outros praticamente não existe diferença.

### Conclusão

A hipótese de que **uma determinada rede de ensino explica isoladamente os melhores resultados não foi confirmada**.

> **A rede de ensino está associada ao resultado em determinados contextos, mas seu comportamento depende fortemente do território.**

Por isso, não encontramos evidência de uma rede consistentemente superior em todos os estados analisados.

---

# 6. Hipótese 3 - Capitais apresentam melhores resultados?

Outra hipótese investigada foi se capitais apresentariam desempenho superior ao interior.

A ideia era verificar se a concentração urbana e administrativa das capitais apareceria refletida nas taxas de alfabetização.

O resultado encontrado foi o contrário.

| Ano  | Capital | Interior |
| ---- | ------: | -------: |
| 2023 |  53,35% |   60,59% |
| 2024 |  55,08% |   63,07% |

No agregado:

* Capital: aproximadamente **54,23%**
* Interior: aproximadamente **61,84%**

O interior apresentou desempenho médio superior nos dois anos analisados.

### Conclusão

A hipótese **não foi confirmada**.

> **Ser capital não representou vantagem automática nas taxas de alfabetização da amostra analisada.**

Esse resultado deve ser interpretado como associação, e não como evidência de que morar no interior cause melhor alfabetização.

Também não foi possível realizar uma comparação adequada entre municípios pequenos e grandes porque a tabela utilizada nessa etapa não possui população municipal.

---

# 7. Análise no nível do aluno

Depois das análises territoriais, descemos para o menor grão disponível: o aluno.

A tabela utilizada foi:

```text
base_modelagem_aluno
```

Ela representa a base Gold preparada para futura classificação supervisionada.

Na amostra analisada encontramos:

* **7.309 alunos**
* **7.309 IDs únicos**
* **5 UFs**
* **2 categorias de rede**

A distribuição do target foi:

| Classificação    | Alunos | Percentual |
| ---------------- | -----: | ---------: |
| Não alfabetizado |  4.697 |     64,26% |
| Alfabetizado     |  2.612 |     35,74% |

---

# 8. Série escolar

A primeira variável analisada foi `serie`.

Entretanto, todos os 7.309 alunos apresentaram:

```text
serie = 2
```

Portanto, não existe variação suficiente para comparar séries.

### Conclusão

> **A série não pode ser utilizada para explicar diferenças de alfabetização nessa amostra.**

Isso é coerente com a origem dos microdados utilizados no projeto, que correspondem ao 2º ano do Ensino Fundamental.

---

# 9. Hipótese 4 -Participação na avaliação está associada à alfabetização?

Em seguida analisamos:

```text
presenca_lp
preenchimento_lp
```

O resultado foi muito forte.

Para `presenca_lp`:

* presentes: 5.697 alunos;
* alfabetizados: 2.612;
* taxa: aproximadamente **45,85%**;
* ausentes: 1.612;
* alfabetizados: **0**.

Quando cruzamos presença com preenchimento:

| Preenchimento | Presença | Alunos | Alfabetizados |   Taxa |
| ------------- | -------- | -----: | ------------: | -----: |
| 0             | 0        |  1.612 |             0 |     0% |
| 0             | 1        |     28 |             0 |     0% |
| 1             | 1        |  5.669 |         2.612 | 46,08% |

Todos os alunos classificados como alfabetizados estavam no grupo com presença e preenchimento válido.

### Conclusão

Existe uma **associação extremamente forte entre participação válida na avaliação e a classificação de alfabetização**.

Entretanto, essa relação exige cuidado.

Presença e preenchimento estão relacionados ao próprio processo de avaliação que permite observar o resultado. Portanto, não podemos interpretar diretamente que presença causa alfabetização.

Além disso, essas variáveis precisam ser avaliadas antes da modelagem para verificar se podem funcionar como um atalho para o target.

---

# 10. Dependência administrativa no nível do aluno

Também analisamos `tp_dependencia`, `rede` e `rede_label`.

Encontramos:

| Categoria | Alunos |   Taxa |
| --------- | -----: | -----: |
| `privada` |  1.700 | 51,06% |
| `total`   |  5.609 | 31,09% |

Existe uma diferença de aproximadamente **20 pontos percentuais** entre os grupos.

Entretanto, não consideramos correto interpretar automaticamente `total` como sinônimo de rede pública.

A semântica dessa categoria precisa ser validada no de-para da fonte antes de qualquer conclusão dessa natureza.

O próprio projeto estabelece que o de-para da rede deve permanecer rastreável à documentação original.

### Conclusão

Existe diferença entre os grupos codificados, mas **não utilizamos essa análise para afirmar superioridade entre ensino público e privado no nível individual**.

---

# 11. Hipótese 5 -A escola está associada ao resultado?

Essa foi uma das análises mais importantes da EDA.

A base contém:

```text
220 escolas distintas
```

Inicialmente calculamos a taxa de alfabetização por escola, utilizando somente escolas com pelo menos 10 alunos.

Encontramos escolas com taxas muito altas e diversas escolas com **0% de alfabetização**.

Entretanto, percebemos um possível problema:

Algumas das escolas com 0% também apresentavam ausência muito elevada dos alunos.

Portanto, uma comparação direta poderia confundir:

```text
desempenho escolar
```

com:

```text
ausência / falta de avaliação
```

Para reduzir esse problema, refizemos a análise considerando somente:

```text
presenca_lp = 1
AND preenchimento_lp = 1
```

e mantendo apenas escolas com pelo menos 10 alunos efetivamente avaliados.

---

# 12. Escola entre alunos efetivamente avaliados

Depois desse controle, a diferença permaneceu extremamente grande.

As melhores escolas apresentaram:

| Escola   | Avaliados | Alfabetizados |   Taxa |
| -------- | --------: | ------------: | -----: |
| 61420784 |        29 |            28 | 96,55% |
| 61400948 |        22 |            21 | 95,45% |
| 61437798 |        34 |            31 | 91,18% |
| 61428332 |        18 |            16 | 88,89% |

Enquanto algumas das menores taxas foram:

| Escola   | Avaliados | Alfabetizados |  Taxa |
| -------- | --------: | ------------: | ----: |
| 61412989 |        17 |             0 |    0% |
| 61433315 |        16 |             0 |    0% |
| 61450013 |        17 |             0 |    0% |
| 61470633 |        20 |             0 |    0% |
| 61470300 |        22 |             1 | 4,55% |
| 61466401 |        44 |             3 | 6,82% |

A diferença não pode ser explicada somente pelo tamanho das amostras.

Por exemplo:

```text
Escola 61410171
45 avaliados
37 alfabetizados
82,22%
```

contra:

```text
Escola 61466401
44 avaliados
3 alfabetizados
6,82%
```

São praticamente a mesma quantidade de alunos avaliados, mas resultados completamente diferentes.

### Conclusão

A hipótese foi **fortemente sustentada pelos dados**.

> **Mesmo considerando somente alunos efetivamente avaliados, encontramos escolas com taxas de alfabetização entre 0% e 96,55%.**

Portanto, a escola aparece como um dos principais fatores observáveis associados às diferenças de alfabetização da amostra.

Isso não significa que a escola, isoladamente, seja a causa do resultado. Características territoriais, socioeconômicas, administrativas e outras variáveis não disponíveis também podem contribuir.

---

# 13. Hipótese 6 -A diferença territorial permanece quando analisamos somente alunos avaliados?

Depois de identificar a importância da participação na avaliação, surgiu uma questão:

> **Será que as diferenças entre UFs eram simplesmente consequência de diferentes níveis de presença e preenchimento?**

Para testar isso, analisamos somente alunos com:

```text
presenca_lp = 1
AND preenchimento_lp = 1
```

O resultado foi:

| UF | Avaliados | Alfabetizados |   Taxa |
| -- | --------: | ------------: | -----: |
| RO |     1.207 |           696 | 57,66% |
| AC |     1.698 |           814 | 47,94% |
| RR |     1.322 |           558 | 42,21% |
| AM |     1.057 |           422 | 39,92% |
| PA |       385 |           122 | 31,69% |

Mesmo depois de restringir a análise aos alunos efetivamente avaliados, existe uma diferença de aproximadamente **26 pontos percentuais entre Rondônia e Pará**.

### Conclusão

A hipótese territorial foi novamente sustentada.

> **As diferenças entre UFs permanecem mesmo quando comparamos somente alunos presentes e com preenchimento válido.**

Isso reforça que a participação na avaliação não explica sozinha a desigualdade territorial encontrada.

---

# 14. Limitação geográfica dos microdados

No nível individual, não realizamos uma análise confiável de capital versus interior.

Embora a base possua `id_municipio`, o município presente no microdado individual é anonimizado e não corresponde necessariamente ao código real do IBGE.

Por isso, a própria arquitetura considera somente a UF como geografia confiável para o aluno e não recomenda o cruzamento desse identificador municipal com a dimensão territorial do IBGE.

Além disso, `capital` e `nome_municipio` não estavam preenchidos na amostra analisada.

Portanto, evitamos produzir uma classificação artificial de capital/interior no nível individual.

---

# 15. Metas educacionais

Também exploramos `meta_vs_resultado`, criada para comparar resultado observado com meta oficial.

Entretanto, durante a EDA encontramos inconsistências nos campos:

```text
meta_taxa
gap_meta
atingiu_meta
atingiu_meta_brasil
```

A consulta inicial retornava zero municípios classificados como tendo atingido ou não atingido a meta, indicando que os campos de classificação não estavam adequadamente populados na amostra importada para a análise.

Também encontramos registros com `meta_taxa` e `gap_meta` nulos.

### Conclusão

> **Não utilizamos `meta_vs_resultado` para sustentar o diagnóstico final da EDA.**

Antes disso, é necessário validar o preenchimento dos campos e garantir que resultado e meta estejam sendo comparados no mesmo grão territorial.

Essa precaução é particularmente importante porque o pipeline foi desenhado para associar metas ao mesmo nível territorial, sem fallback de meta municipal para meta estadual.

---

# 16. Evolução temporal

A tabela `evolucao_temporal` também foi explorada.

No agregado encontramos:

```text
2023 -> taxa média aproximada de 59,89%
2024 -> taxa média aproximada de 62,17%
```

A classificação de tendência em 2024 apresentou:

```text
Alta      2.839
Queda     2.090
Estável      12
Nulo        117
```

Embora exista uma melhora agregada entre os anos, decidimos não utilizar essa análise como uma das principais evidências do diagnóstico.

A tabela combina diferentes níveis territoriais e redes. Portanto, uma análise temporal definitiva exige controlar rigorosamente o mesmo território, rede e grão ao comparar os anos.

### Conclusão

A evolução temporal foi considerada **evidência exploratória**, mas não uma conclusão central deste diagnóstico.

---

# 17. Principais descobertas

Depois de analisar território, rede, município, participação, escola e aluno, chegamos aos seguintes resultados.

### Território

**Hipótese parcialmente confirmada.**

Existem diferenças relevantes entre regiões e UFs, mas também grande desigualdade entre municípios pertencentes ao mesmo estado.

### Rede de ensino

**Não explica isoladamente o resultado.**

Nenhuma rede apresentou superioridade consistente em todas as UFs.

### Capital × interior

**Hipótese de vantagem das capitais não confirmada.**

O interior apresentou média superior nos dois anos analisados.

### Série

**Não foi possível testar.**

Todos os alunos da amostra pertencem à segunda série.

### Participação na avaliação

**Forte associação observada.**

Todos os alunos alfabetizados estavam entre aqueles com participação e preenchimento válidos, mas essa variável está diretamente relacionada ao processo de mensuração e exige cuidado na interpretação e modelagem.

### Escola

**Uma das associações mais fortes encontradas.**

Mesmo considerando somente alunos avaliados e escolas com pelo menos 10 avaliações, encontramos taxas entre **0% e 96,55%**.

### UF no nível individual

**Forte associação observada.**

Entre alunos efetivamente avaliados, as taxas variaram de **31,69% no Pará a 57,66% em Rondônia**.

---

# 18. Storytelling da análise

A investigação pode ser resumida da seguinte forma:

```text
Encontramos grande desigualdade entre municípios
                    ↓
O território parece importar
                    ↓
Mas existem grandes diferenças dentro das próprias UFs
                    ↓
Será que a rede de ensino explica?
                    ↓
Não de forma consistente
                    ↓
Será que capitais apresentam vantagem?
                    ↓
Também não
                    ↓
Descemos para o nível do aluno
                    ↓
Participação na avaliação está fortemente associada ao resultado
                    ↓
Controlamos presença e preenchimento
                    ↓
Mesmo assim, encontramos enorme diferença entre escolas
                    ↓
E as diferenças entre UFs continuam existindo
                    ↓
A desigualdade é multifatorial
```

---

# 19. Diagnóstico final

As desigualdades de alfabetização **não são explicadas por um único fator**.

Os dados mostram que **escola, participação regular do aluno nas avaliações e contexto territorial estão fortemente associados aos resultados de alfabetização**, enquanto rede de ensino e condição de capital, isoladamente, não explicam o padrão observado.

Nosso diagnóstico aponta que os melhores resultados se concentram em contextos nos quais existe participação efetiva dos alunos, melhores resultados no nível escolar e territórios com desempenho educacional mais elevado.

Mesmo depois de controlar presença e preenchimento da avaliação, encontramos diferenças expressivas entre escolas e UFs.

Dessa forma, **escola, participação do aluno e território constituem os principais fatores observáveis associados às diferenças de alfabetização identificadas nesta análise.**

---

# 20. O que ainda não conseguimos explicar

A EDA permite identificar **onde a desigualdade aparece**, mas não todas as causas responsáveis por ela.

Os resultados levantam hipóteses relacionadas a:

* condições socioeconômicas;
* renda familiar;
* escolaridade dos responsáveis;
* valorização da educação;
* perspectiva educacional e profissional;
* infraestrutura escolar;
* disponibilidade e formação de professores;
* gestão educacional;
* políticas municipais e estaduais;
* acesso e permanência dos alunos na escola.

Essas variáveis não estão suficientemente representadas na base atual.

Portanto, não afirmamos que elas causam as diferenças encontradas.

Elas representam **hipóteses para uma próxima etapa de investigação**.

O próprio projeto reconhece que a base atual possui poucas variáveis explicativas e que uma utilização analítica mais avançada exige enriquecimento socioeconômico e educacional.

---

# 21. Próximos passos

A partir desta EDA, uma evolução natural seria enriquecer a base com novas dimensões, mantendo o mesmo cuidado de granularidade e proveniência.

Algumas possibilidades:

```text
Aluno
  +
Escola
  +
Município / UF
  +
Indicadores socioeconômicos
  +
Infraestrutura escolar
  +
Indicadores docentes
  +
Contexto familiar
        ↓
Modelo analítico mais completo
```

Isso permitiria sair da pergunta:

> **Onde estão as maiores diferenças de alfabetização?**

para uma pergunta mais profunda:

> **Quais características ajudam a explicar essas diferenças?**

A camada `gold.base_modelagem_aluno` já foi construída no grão individual justamente como fundação para uma futura classificação supervisionada, mantendo `alfabetizado_oficial` como target e removendo informações diretamente derivadas da proficiência para evitar data leakage.

---

# 22. Conclusão

A análise mostrou que olhar apenas para médias nacionais ou regionais esconde uma parcela importante do problema.

A desigualdade aparece:

**entre regiões -> entre UFs -> dentro das UFs -> entre municípios -> entre escolas -> entre alunos.**

Ao testar explicações simples, verificamos que nem a rede de ensino nem a condição de capital são suficientes para explicar o fenômeno isoladamente.

Por outro lado, encontramos diferenças fortes e persistentes relacionadas ao **território, à escola e à participação efetiva do aluno na avaliação**.

O principal resultado desta EDA, portanto, não é apontar uma causa única para a alfabetização infantil.

É demonstrar, com os dados disponíveis, que **o desempenho educacional está inserido em um contexto territorial e escolar heterogêneo e que compreender essa desigualdade exige analisar esses fatores conjuntamente.**
