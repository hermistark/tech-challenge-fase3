# 📚 Enriquecimento de Dados e Engenharia de Atributos - Alfabetização Brasil

## 🎯 Objetivo

Este documento detalha o processo completo de **enriquecimento externo** dos dados de alfabetização e a **engenharia de atributos** realizada para criar um dataset robusto para análise e modelagem preditiva.

---

## 📊 Arquitetura de Dados - Medallion (Bronze → Silver → Gold)

```
┌─────────────────────────────────────────────────────────────────┐
│                         BRONZE LAYER                             │
│                    (Dados Brutos - Delta)                        │
├─────────────────────────────────────────────────────────────────┤
│  • avaliacao_alfabetizacao (SAEB/INEP)                          │
│  • uf (IBGE - Diretório de UFs)                                 │
│  • fundeb_educacao_infantil (Portaria 11/2026)                  │
│  • fundeb_vaat_cronograma                                        │
│  • fundeb_vaar_redes                                             │
│  • fundeb_vaar_cronograma                                        │
│  • fundeb_educacao_profissional (18.200 instituições)           │
│  • fundeb_aee (75.300 instituições com AEE)                     │
│  • fundeb_conveniadas (18.993 instituições)                     │
│  • pnad_variaveis (Pesquisa Nacional 1997)                      │
│  • pnad_proporcao_baixa_escolaridade                            │
│  • pnad_media_anos_estudo                                        │
│  • pnad_media_estudo_renda                                       │
│  • pnad_taxa_escolarizacao                                       │
│  • pnad_defasagem_idade_serie                                    │
│  • censo_escolar_dicionario                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         SILVER LAYER                             │
│                  (Features Derivadas - Delta)                    │
├─────────────────────────────────────────────────────────────────┤
│  • alfabetizacao_evolucao_temporal (7 features)                 │
│  • alfabetizacao_performance (9 features)                       │
│  • alfabetizacao_indices_compostos (5 features)                 │
│  • alfabetizacao_regional (7 features)                          │
│  • alfabetizacao_feature_store (37 features consolidadas)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          GOLD LAYER                              │
│                   (Análises & Dashboards)                        │
├─────────────────────────────────────────────────────────────────┤
│  • Análise Exploratória (notebook 03)                           │
│  • Dashboards de BI                                              │
│  • Modelos de ML (próxima fase)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Fontes de Enriquecimento (Bronze Layer)

### 1. **INEP - Instituto Nacional de Estudos e Pesquisas Educacionais**

#### 1.1 Avaliação de Alfabetização (SAEB)
- **Descrição**: Taxa de alfabetização por UF, ano, série e rede
- **Tabela**: `workspace.bronze.avaliacao_alfabetizacao`
- **Campos-chave**: ano, sigla_uf, serie, rede, taxa_alfabetizacao
- **Particionamento**: Por ano e sigla_uf
- **Fonte**: br_inep_avaliacao_alfabetizacao_uf.csv.gz

#### 1.2 Censo Escolar - Dicionário
- **Descrição**: Códigos e descrições de rede, localização, dependência administrativa
- **Tabela**: `workspace.bronze.censo_escolar_dicionario`
- **Campos-chave**: nome_coluna, chave, cobertura_temporal, valor
- **Registros**: Metadados de classificação escolar

---

### 2. **IBGE - Instituto Brasileiro de Geografia e Estatística**

#### 2.1 Diretório de UFs
- **Descrição**: Nomes completos, siglas e região geográfica de cada UF
- **Tabela**: `workspace.bronze.uf`
- **Campos-chave**: sigla, nome, regiao
- **Registros**: 27 UFs (26 estados + DF)

---

### 3. **FUNDEB - Fundo de Manutenção e Desenvolvimento da Educação Básica**

#### Portaria 11/2026 - Complementações VAAT e VAAR

| Tabela | Descrição | Registros | Status |
|--------|-----------|-----------|--------|
| `fundeb_educacao_infantil` | Indicadores de educação infantil por ente federado | - | ⚠️ Upload pendente |
| `fundeb_vaat_cronograma` | Cronograma de distribuição VAAT | - | ⚠️ Upload pendente |
| `fundeb_vaar_redes` | Redes beneficiadas e coeficientes VAAR | - | ⚠️ Upload pendente |
| `fundeb_vaar_cronograma` | Cronograma de distribuição VAAR | - | ⚠️ Upload pendente |
| `fundeb_educacao_profissional` | Instituições de educação profissional | 18.200 | ✅ Pronto |
| `fundeb_aee` | Instituições com AEE (Atendimento Educacional Especializado) | 75.300 | ✅ Pronto |
| `fundeb_conveniadas` | Instituições conveniadas ao FUNDEB | 18.993 | ✅ Pronto |

**Campos relevantes**: entidade_federativa, valor_complementacao, coeficiente, numero_instituicoes

---

### 4. **PNAD - Pesquisa Nacional por Amostra de Domicílios (1997)**

#### Base IBGE - Séries Históricas de Educação

| Tabela | Descrição | Arquivo Fonte |
|--------|-----------|---------------|
| `pnad_variaveis` | Variáveis e métricas de dimensões educacionais | PNAD_ajuste_variaveis_e_analise_metricas_dimenssoes_12_11_2013.csv |
| `pnad_proporcao_baixa_escolaridade` | Proporção de jovens 15-24 anos com menos de 4 anos de estudo | PNAD97-edutab02.csv |
| `pnad_media_anos_estudo` | Média de anos de estudo por idade e região | PNAD97-edutab03.csv |
| `pnad_media_estudo_renda` | Média de anos de estudo por renda familiar per capita | PNAD97-edutab04.csv |
| `pnad_taxa_escolarizacao` | Taxas de escolarização por faixa etária | PNAD97-edutab05.csv |
| `pnad_defasagem_idade_serie` | Defasagem idade/série (7 a 14 anos) | PNAD97-edutab06.csv |

**Observações**:
- Arquivos originais em formato BIFF5 (Excel 5.0/7.0) foram convertidos para CSV
- Múltiplas linhas de cabeçalho removidas via filtros SQL
- Leitura com `multiLine=true` para preservar estrutura

---

## 🔧 Engenharia de Atributos (Silver Layer)

### 📈 **1. Evolução Temporal** (`alfabetizacao_evolucao_temporal`)

Features que capturam mudanças ao longo do tempo:

| Feature | Descrição | Fórmula |
|---------|-----------|---------|  
| `delta_ano_anterior` | Variação absoluta ano a ano | `taxa_atual - taxa_anterior` |
| `variacao_percentual` | Variação percentual ano a ano | `((taxa_atual - taxa_anterior) / taxa_anterior) * 100` |
| `aceleracao` | Taxa de mudança da variação | `variacao_atual - variacao_anterior` |
| `media_movel_3anos` | Suavização de tendência (janela de 3 anos) | `AVG(taxa) OVER (ORDER BY ano ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` |
| `desvio_media_movel` | Distância da taxa atual para a média móvel | `taxa - media_movel_3anos` |
| `tendencia` | Classificação de tendência | `CASE WHEN variacao > 0 THEN 'CRESCENTE' WHEN variacao < 0 THEN 'DECRESCENTE' ELSE 'ESTÁVEL'` |

**Registros**: 145 (25 UFs × múltiplas redes × anos)

---

### 🏆 **2. Indicadores de Performance** (`alfabetizacao_performance`)

Features de benchmarking e comparação:

| Feature | Descrição | Fórmula |
|---------|-----------|---------|  
| `ranking_nacional` | Posição no ranking nacional | `RANK() OVER (PARTITION BY ano ORDER BY taxa DESC)` |
| `ranking_denso` | Ranking sem empates | `DENSE_RANK() OVER (PARTITION BY ano ORDER BY taxa DESC)` |
| `percentil_performance` | Percentil de performance (0-100) | `PERCENT_RANK() OVER (PARTITION BY ano ORDER BY taxa) * 100` |
| `quartil` | Quartil de classificação (1-4) | `NTILE(4) OVER (PARTITION BY ano ORDER BY taxa)` |
| `classificacao_quartil` | Label do quartil | `CASE quartil WHEN 1 THEN 'BAIXO (Q1)' WHEN 4 THEN 'ALTO (Q4)' ...` |
| `media_nacional` | Média nacional do ano | `AVG(taxa) OVER (PARTITION BY ano)` |
| `distancia_media_nacional` | Distância da média nacional | `taxa - media_nacional` |
| `z_score` | Score padronizado (unidades de desvio padrão) | `(taxa - media) / desvio_padrao` |
| `gap_desigualdade_nacional` | Gap entre máximo e mínimo nacional | `MAX(taxa) - MIN(taxa) OVER (PARTITION BY ano)` |

**Registros**: 145

---

### 💯 **3. Índices Compostos** (`alfabetizacao_indices_compostos`)

Métricas agregadas para avaliação holística:

| Feature | Descrição | Fórmula/Componentes |
|---------|-----------|---------------------|
| `indice_alfabetizacao_consolidado` | Score 0-100 combinando taxa atual, variação e estabilidade | `0.7*taxa + 0.2*variacao_norm + 0.1*estabilidade_norm` |
| `score_progresso` | Score de melhoria ao longo do tempo | Baseado em variação percentual e aceleração |
| `volatilidade_3anos` | Desvio padrão da taxa nos últimos 3 anos | `STDDEV(taxa) OVER (ORDER BY ano ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` |
| `classificacao_estabilidade` | Categoria de estabilidade | `CASE WHEN volatilidade < 1 THEN 'MUITO ESTÁVEL' WHEN < 3 THEN 'ESTÁVEL' WHEN < 7 THEN 'MODERADAMENTE VOLÁTIL' ELSE 'ALTA VOLATILIDADE'` |
| `score_final_ponderado` | Score geral (média ponderada dos 2 scores anteriores) | `0.5*indice_consolidado + 0.5*score_progresso` |

**Registros**: 145

---

### 🗺️ **4. Enriquecimento Regional** (`alfabetizacao_regional`)

Features contextuais por região geográfica:

| Feature | Descrição |
|---------|-----------|  
| `regiao_geografica` | Região da UF (Norte, Nordeste, Sul, Sudeste, Centro-Oeste) |
| `media_regional` | Média da taxa na região |
| `desvio_padrao_regional` | Dispersão dentro da região |
| `min_regional` | Taxa mínima na região |
| `max_regional` | Taxa máxima na região |
| `ranking_regional` | Ranking dentro da região |
| `distancia_media_regional` | Distância da média regional |
| `gap_desigualdade_regional` | Gap entre máximo e mínimo na região |

**Registros**: 145

---

### 📦 **5. Feature Store Consolidado** (`alfabetizacao_feature_store`)

Tabela única unificando **todas as 37 features** derivadas, pronta para:
- Análise exploratória  
- Modelagem preditiva
- Dashboards interativos
- APIs de inferência

**Schema**:
```sql
ano, sigla_uf, nome_uf, regiao_geografica, rede, taxa_alfabetizacao,
-- Evolução (7)
delta_ano_anterior, variacao_percentual, aceleracao, media_movel_3anos, 
desvio_media_movel, tendencia,
-- Performance (9)
ranking_nacional, ranking_denso, percentil_performance, quartil, 
classificacao_quartil, media_nacional, distancia_media_nacional, 
z_score, gap_desigualdade_nacional,
-- Índices (5)
indice_alfabetizacao_consolidado, score_progresso, volatilidade_3anos, 
classificacao_estabilidade, score_final_ponderado,
-- Regional (7)
media_regional, desvio_padrao_regional, min_regional, max_regional, 
ranking_regional, distancia_media_regional, gap_desigualdade_regional
```

**Registros**: 145 (25 UFs, 4 redes, 2 anos)

---

## 🚀 Como Executar o Pipeline

### **Passo 1: Bronze - Ingestão de Dados**

**Notebook**: `01_bronze_batch`

1. Suba os arquivos CSV para `/Volumes/workspace/bronze/raw_files/`
2. Execute as células SQL na ordem:
   - Célula 5: Avaliação Alfabetização ✅
   - Célula 7: UF (IBGE) ✅
   - Células 20, 22, 24, 26, 28: PNAD Tabelas 2-6 ✅
   - Célula 30: Censo Escolar Dicionário ✅
   - Células 32, 34, 36: FUNDEB (Profissional, AEE, Conveniadas) ✅
3. Execute célula 38 para validação

**Status**: 12 de 19 tabelas prontas | 7 aguardando upload manual

---

### **Passo 2: Silver - Engenharia de Features**

**Notebook**: `02_silver_feature_engineering`

Execute as células SQL na ordem:
1. Célula 4: `alfabetizacao_evolucao_temporal` ✅
2. Célula 6: `alfabetizacao_performance` ✅
3. Célula 8: `alfabetizacao_indices_compostos` ✅
4. Célula 10: `alfabetizacao_regional` ✅
5. Célula 12: `alfabetizacao_feature_store` ✅
6. Célula 14: Validação ✅

**Status**: ✅ Todas as 5 tabelas silver criadas (145 registros cada)

---

### **Passo 3: Gold - Análise Exploratória**

**Notebook**: `03_analise_exploratoria_alfabetizacao`

Execute todas as células Python/SQL (células 2, 4, 5, 7-25)

**Outputs**:
- 📊 Estatísticas descritivas
- 📈 6 visualizações (gráficos de linha, boxplots, barras, heatmap)
- 💡 Insights automáticos sobre alfabetização no Brasil

**Status**: ✅ Análise completa executada

---

## 📈 Principais Insights (2024)

### 🎯 **Cobertura de Dados**
- **145 registros** de alfabetização
- **Período**: 2023-2024
- **25 UFs** brasileiras  
- **4 redes** de ensino

### 🏆 **Ranking Regional**
1. **Sudeste**: 68,09% (melhor região)
2. **Centro-Oeste**: 61,97%
3. **Sul**: 57,95%
4. **Nordeste**: 54,28%
5. **Norte**: 52,11%

### ⭐ **Top Performers**
- 🥇 **ES (Espírito Santo) - Rede 2**: 86,21%
- 🥈 **CE (Ceará) - Redes 3 e 5**: ~85,3%
- 🥉 **GO (Goiás) - Rede 2**: 83,66%

### 📉 **Bottom Performers**
- **BA (Bahia)**: 34,46% - 35,96%
- **SE (Sergipe)**: ~38%
- **AP (Amapá)**: 39,56%

### 📊 **Tendências**
- **62,7%** das UFs em **crescimento** (47 UFs)
- **29,3%** em queda (22 UFs)
- **74,7%** estáveis ou muito estáveis

### 🚀 **Maiores Crescimentos**
- **PI (Piauí) - Rede 2**: +53,20% 🔥
- **SE (Sergipe)**: +22% a +24%
- **SP (São Paulo)**: +22,38%

### ⚖️ **Desigualdade**
- **Gap nacional**: 51,75 pontos percentuais
- **Região mais desigual**: Centro-Oeste (CV: 19,73%)
- **Região mais homogênea**: Norte (CV: 12,85%)

---

## 🛠️ Tecnologias Utilizadas

- **Databricks**: Plataforma de processamento
- **Apache Spark**: Motor de processamento distribuído
- **Delta Lake**: Formato de storage (ACID transactions)
- **SQL**: Transformações e agregações
- **Python**: Análise exploratória
- **Pandas**: Manipulação de dados  
- **Matplotlib + Seaborn**: Visualizações
- **Unity Catalog**: Governança de dados

---

## 📂 Estrutura de Diretórios

```
tech-challenge-fase2-alfabetizacao/
├── notebooks/
│   ├── 01_bronze_batch.ipynb              # Ingestão de dados brutos
│   ├── 02_silver_feature_engineering.ipynb # Features derivadas
│   └── 03_analise_exploratoria_alfabetizacao.ipynb # EDA e insights
├── data/
│   └── /Volumes/workspace/bronze/raw_files/ # Arquivos CSV fonte
├── ENRIQUECIMENTO_E_FEATURES.md           # Este documento
└── README.md                               # Documentação principal
```

---

## 📌 Próximos Passos

### **Gold Layer - Agregações Analíticas**
- [ ] Criar tabela `alfabetizacao_agregada_anual`
- [ ] Criar tabela `alfabetizacao_agregada_regional`
- [ ] Criar views para dashboards

### **Modelagem Preditiva**
- [ ] Previsão de taxa de alfabetização futura
- [ ] Identificação de UFs em risco
- [ ] Recomendações de investimento

### **Dashboards**
- [ ] Dashboard executivo (Lakeview)
- [ ] Dashboard regional comparativo
- [ ] Dashboard de tendências temporais

### **Enriquecimento Adicional**
- [ ] Upload dos 5 arquivos FUNDEB pendentes
- [ ] Integração com dados socioeconômicos (PIB, IDH)
- [ ] Dados de investimento em educação por UF

---

## 👥 Autores

**Tech Challenge - Fase 2 - Alfabetização**  
Projeto de análise de dados educacionais do Brasil

---

## 📝 Changelog

### v1.0.0 (2024-09-11)
- ✅ 19 tabelas bronze configuradas (12 prontas, 7 pendentes)
- ✅ 5 tabelas silver com 37 features derivadas
- ✅ Feature store consolidado (145 registros)
- ✅ Análise exploratória completa
- ✅ 6 visualizações e insights automáticos

---

## 📄 Licença

Este projeto é parte do programa de formação em Data Science e está disponível para fins educacionais.

---

**Documentação atualizada em**: 11 de setembro de 2026  
**Versão**: 1.0.0
