# Notebooks

Formato Databricks (`.py` com células `# COMMAND ----------`), na ordem de execução:

- `00_enriquecimento_fundeb.py`: limpa e agrega as instituições FUNDEB por UF, junta na base de aluno.
- `01_eda.py`: análise exploratória, hipóteses territoriais/de rede/de escola e desbalanceamento do target.
- `02_modelagem.py`: pipeline sklearn (imputação, encoding, RandomForest), split 80/20, validação cruzada, registro no MLflow.
- `03_interpretabilidade.py`: Feature Importance nativa e SHAP values, a partir do modelo já treinado.
- `04_aplicacao_estrategica.py`: risco por município (nomeado, via `gold.indicador_municipio`), agrupamento regional e proxy de risco de meta futura.
- `05_dashboard.py`: painel executivo HTML consolidando os 4 anteriores.

Cada notebook depende do anterior ter rodado (o `03`, `04` e `05` carregam o modelo do MLflow que o `02` registra).
