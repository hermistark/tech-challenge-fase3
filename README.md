# Tech Challenge - Fase 3

## Predicao e inteligencia analitica para alfabetizacao no Brasil

Projeto da Fase 3 do Tech Challenge, baseado na tabela oficial `gold.base_modelagem_aluno`, produzida na Fase 2 com dados INEP/IBGE.

## Objetivo

Investigar os fatores associados a `alfabetizado_oficial` e construir um pipeline de Machine Learning reproduzivel para identificar alunos e municipios com maior risco educacional, apoiando a tomada de decisao em politicas publicas.

## Base de dados

- Origem: Databricks, tabela `gold.base_modelagem_aluno`.
- Volume de referencia: 2.120.560 registros.
- Granularidade: aluno.
- Target: `alfabetizado_oficial` (0/1).
- Colunas disponiveis: ano, UF, municipio, regiao, capital, serie, escola, dependencia, rede, presenca, preenchimento, caderno, peso e metadados de origem.
- A proficiencia (`VL_PROFICIENCIA_LP`) foi excluida da base de modelagem porque deriva diretamente do desempenho usado no target e causaria data leakage.

A base nao e versionada neste repositorio. O time deve documentar o caminho de exportacao ou a consulta Databricks usada para reproduzir os dados.

## Estrutura

```text
tech-challenge-fase3/
├── data/
├── notebooks/
├── src/
│   ├── preprocessing/
│   ├── modeling/
│   ├── evaluation/
│   └── visualization/
├── reports/
├── images/
├── requirements.txt
├── README.md
└── .gitignore
```

## Fluxo de trabalho

1. Executar a EDA e avaliar distribuicoes, correlacoes e desbalanceamento do target.
2. Registrar hipoteses analiticas e decidir quais variaveis podem ser usadas sem leakage indireto.
3. Integrar enriquecimentos externos, quando houver fonte oficial e chave de join validada.
4. Separar treino, validacao e teste de forma reprodutivel.
5. Treinar modelos com imputacao, encoding e transformacoes dentro do Pipeline do sklearn.
6. Fazer tuning com validacao cruzada, usando amostragem estratificada quando necessario por causa do volume.
7. Avaliar generalizacao com F1, ROC-AUC, recall por classe, matriz de confusao e metricas por grupo.
8. Produzir feature importance e SHAP values, traduzindo os resultados para linguagem de negocio.
9. Responder as perguntas estrategicas e registrar limitacoes, riscos e evolucoes futuras.

## Perguntas de negocio

- Quais fatores mais impactam a alfabetizacao?
- Quais municipios apresentam maior risco educacional?
- Quais regioes possuem padroes semelhantes?
- Como prever municipios que podem nao atingir metas futuras?
- Quais variaveis exercem maior influencia nos modelos?

## Reproducao

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Os notebooks e scripts devem receber uma exportacao da tabela oficial ou uma consulta Databricks documentada. Nenhum dado simulado deve ser usado para gerar resultados finais.

## Governanca Git

Cada frente deve trabalhar em branch propria, abrir Pull Request e registrar revisao antes do merge na branch principal. Commits devem ser pequenos e descrever uma unidade de trabalho.

## Limitacoes e evolucoes futuras

- Validar possivel leakage indireto em serie, presenca e preenchimento.
- Avaliar enriquecimento com Censo Escolar, FUNDEB, PNAD ou Atlas do Desenvolvimento Humano.
- Definir estrategia de monitoramento de drift e atualizacao anual.
- Confirmar equidade das previsoes entre regioes, redes e grupos de alunos.

## Equipe

Atualizar os nomes conforme a distribuicao final das quatro frentes descritas no plano de execucao.
