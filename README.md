# 🏎️ F1 Lake — Pipeline de Dados e ML para Previsão de Campeões de F1

Pipeline de dados end-to-end que coleta dados históricos de Fórmula 1, os organiza em uma arquitetura de Data Lakehouse (camadas Bronze/Silver/Gold) e treina um modelo de Machine Learning para prever se um piloto será campeão da temporada, com base em seu histórico recente de performance.

O projeto cobre o ciclo completo de um caso de uso de dados: **ingestão → armazenamento → transformação → feature engineering → modelagem → serving**.

> **Nota sobre o repositório**: apenas a etapa de **coleta e envio de dados** (`main.py`, `collect.py`, `sender.py`) é de fato executada localmente/neste código. As pastas `etl/` e `ml_champion/` são a **representação em código** das queries e notebooks que rodam no **Databricks** — ou seja, os arquivos `.sql` e os scripts de transformação/treino documentam a lógica que foi executada diretamente no workspace do Databricks (Spark Declarative Pipelines, Unity Catalog, MLflow gerenciado), e não um pipeline local end-to-end.

---

## 🎯 Problema de negócio

Dado o histórico de resultados de um piloto de F1 (posições de largada, pódios, poles, ultrapassagens, pontos, etc.), qual a probabilidade dele ser campeão da temporada atual? O modelo final expõe essa probabilidade via uma API própria, podendo ser consumida por dashboards ou outras aplicações.

---

## 🏗️ Arquitetura

O projeto segue uma **arquitetura medalhão (medallion architecture)**, com duas frentes de execução distintas:

- 🖥️ **Local** (este repositório, executado via `python main.py`): extração dos dados da API de F1 e envio para o Data Lake na AWS.
- ☁️ **Databricks** (queries e notebooks — representados aqui em `.sql`/`.py`, mas rodados no workspace): todas as transformações (Bronze → Silver → Gold) e todo o ciclo de Machine Learning (treino, tracking e serving).

`main.py` (raiz) orquestra o processo de coleta e envio **em loop contínuo**, rodando o ciclo a cada 6 horas — a única parte do pipeline pensada para rodar continuamente fora do Databricks.

---

## 🧩 Camadas do pipeline

### 1. Ingestão e carga (execução local — `main.py`)

- **`collect.py`**: usa a biblioteca [FastF1](https://github.com/theOehrly/Fast-F1) para extrair resultados de corridas (Race e Sprint) de múltiplas temporadas (2020–2026), enriquecendo cada registro com metadados do evento (país, local, rodada, data). Os dados são salvos localmente em **Parquet**, formato colunar mais eficiente que CSV para pipelines analíticos.
- **`sender.py`**: envia os arquivos Parquet gerados para um bucket **AWS S3** via `boto3` — a camada *raw/bronze* do lakehouse — e remove os arquivos locais após o upload confirmado.
- **`main.py`**: laço que executa coleta + envio a cada 6 horas, mantendo o lake atualizado incrementalmente com novas corridas.

Essa é a única parte do repositório pensada para ser executada como está, fora de um ambiente Databricks.

### 2. Transformação — Bronze → Silver → Gold (código representando execução no Databricks)

A partir daqui, os arquivos em `etl/` **documentam** a lógica rodada em notebooks/queries do workspace Databricks, usando **PySpark**, **Spark Declarative Pipelines** e **Unity Catalog** para versionamento e governança de tabelas:

- **`etl/fs_driver.sql`** / **`etl/fs_f1_drivers_all.sql`**: constroem uma *Feature Store* de pilotos — para cada data de referência, calculam estatísticas de performance (pódios, poles, ultrapassagens, posição média de largada e chegada) considerando diferentes janelas históricas (últimas 10, 20, 40 corridas e carreira completa).
- **`etl/main.py`**: mesma lógica reescrita com a API declarativa do PySpark (`@dp.materialized_view`), formato usado para rodar como pipeline gerenciado no Databricks.
- **`etl/f1_champion.sql`**: identifica o campeão de cada temporada via `ROW_NUMBER()` sobre a soma de pontos por piloto/ano.
- **`etl/abt_f1_drivers_champion.sql`**: monta a **ABT (Analytical Base Table)** final na camada Gold (`lakehouse.gold.abt_f1_drivers_champion`), unindo a feature store com a flag de campeão (`flChampion`) — a tabela usada diretamente pelo modelo de ML.

### 3. Machine Learning (código representando execução no Databricks)

Pasta **`ml_champion/`** — também roda no workspace Databricks, aproveitando o MLflow gerenciado nativamente pela plataforma:

- **`train.py`**: pipeline de treino com `scikit-learn`, seguindo a metodologia **SEMMA**:
  - Amostragem estratificada (treino/teste) e separação de um período *out-of-time* (2025) para validar a robustez temporal do modelo
  - Tratamento de valores ausentes com `feature-engine` (`ArbitraryNumberImputer`)
  - Modelo: `RandomForestClassifier`
  - Rastreamento completo do experimento com **MLflow**: métricas de ROC AUC, curva ROC, importância de features e o modelo versionado no Model Registry
- **`app.py`**: API de *model serving* com **Flask**, que carrega a versão mais recente do modelo registrada no MLflow e expõe:
  - `GET /health_check`
  - `POST /predict` — recebe features de um ou mais pilotos e retorna a probabilidade de título
- **`feature_importances.md`** / **`roc_curve.png`**: artefatos de avaliação do modelo, exportados do experimento rodado no Databricks.

**Resultados do modelo** (registrados no MLflow tracking):

| Conjunto | ROC AUC |
|---|---|
| Treino | 0.995 |
| Teste | 0.9999 |
| Out-of-time (2025) | 0.955 |

As features mais relevantes são as relacionadas à **posição média de largada nas últimas 10–40 corridas** e à **quantidade de poles/vitórias recentes**, o que faz sentido no domínio: performance recente de qualificação é um forte preditor de título.

> Nota: a diferença entre AUC de teste (quase 1.0) e AUC out-of-time (0.955) sugere que o corte temporal *out-of-time* é a validação mais realista da capacidade de generalização do modelo — um ponto interessante para discutir em entrevista técnica sobre *data leakage* e validação temporal em séries históricas.

---

## 🛠️ Stack de tecnologias

| Categoria | Ferramenta | Uso no projeto | Onde roda |
|---|---|---|---|
| Linguagem | **Python 3.12** | Toda a lógica de extração, orquestração e ML | Local + Databricks |
| Coleta de dados | **FastF1** | API não-oficial de telemetria e resultados de F1 | Local |
| Processamento de dados | **Pandas**, **PyArrow (Parquet)** | Manipulação e armazenamento colunar eficiente | Local |
| Cloud / Storage | **AWS S3 (boto3)** | Camada de armazenamento bruto do Data Lake | Local → S3 |
| Big Data / Lakehouse | **PySpark**, **Spark Declarative Pipelines**, **Unity Catalog** | Transformações declarativas e governança em arquitetura medalhão | Databricks |
| Orquestração de lakehouse | **Nekt SDK** | Leitura/gestão de tabelas do lakehouse | Databricks / local (export) |
| Machine Learning | **scikit-learn** (RandomForest), **feature-engine** | Modelagem preditiva e tratamento de dados faltantes | Databricks |
| MLOps | **MLflow** (tracking + model registry) | Rastreabilidade de experimentos e versionamento de modelos | Databricks (gerenciado) |
| Serving | **Flask** | API REST para consumo do modelo em produção | Databricks / local |
| Ambiente / DevOps | **Dev Containers (Docker)**, **python-dotenv** | Ambiente de desenvolvimento reprodutível com Java + Spark | Local |

---

## 📁 Estrutura do repositório

```
f1-lake/
├── collect.py              # [LOCAL] Extração dos dados via FastF1
├── sender.py                # [LOCAL] Upload dos arquivos para S3
├── main.py                  # [LOCAL] Orquestração do loop de coleta + envio
├── etl/                      # [DATABRICKS] Representação das queries/notebooks
│   ├── fs_driver.sql              # Feature store (SQL puro)
│   ├── fs_f1_drivers_all.sql      # Feature store completa (múltiplas janelas)
│   ├── f1_champion.sql            # Identificação do campeão da temporada
│   ├── abt_f1_drivers_champion.sql# ABT final (camada Gold)
│   ├── main.py                    # Pipeline declarativo em PySpark
├── ml_champion/               # [DATABRICKS] Representação do notebook de ML
│   ├── train.py               # Treino do modelo + tracking MLflow
│   ├── app.py                  # API Flask de serving do modelo
│   ├── predict.py              # Script de teste da API
│   ├── feature_importances.md  # Importância das variáveis
│   └── roc_curve.png           # Curva ROC do modelo
├── .devcontainer/             # Ambiente de desenvolvimento local (Docker + Spark + Jupyter)
└── data/                      # Dados intermediários (parquet/csv) da etapa local
```

---

## ▶️ Como executar

### Etapa local (coleta e envio)

1. Clone o repositório e abra em um **Dev Container** (recomendado — já inclui Java, Spark e Jupyter configurados) ou instale as dependências manualmente.
2. Configure as variáveis de ambiente em um arquivo `.env`:
   ```
   AWS_KEY=...
   AWS_SECRET_KEY=...
   BUCKET_NAME=...
   ```
3. Rode a coleta e o envio contínuo dos dados:
   ```bash
   python main.py
   ```

### Etapa Databricks (transformação e ML)

Os arquivos em `etl/` e `ml_champion/` foram desenhados para rodar no workspace Databricks:

4. Publique as queries de `etl/*.sql` (ou o pipeline declarativo `etl/main.py`) como uma **Lakeflow Pipeline**, apontando `f1_results` (camada Bronze, alimentada a partir do S3) como fonte.
5. Rode `ml_champion/train.py` em um notebook Databricks — o MLflow tracking é gerenciado automaticamente pelo workspace.
6. `ml_champion/app.py` pode ser servido tanto localmente quanto via Databricks Model Serving, carregando o modelo do Model Registry.

---

## 💡 Principais aprendizados e destaques técnicos

- Separação clara entre a etapa **operacional/local** (ingestão contínua de dados) e a etapa **analítica/gerenciada** (transformação e ML no Databricks), refletindo como pipelines de dados reais costumam ser distribuídos entre diferentes ambientes de execução.
- Aplicação prática de **arquitetura medalhão** (Bronze/Silver/Gold) em um cenário real de dados esportivos.
- Uso de **Spark Declarative Pipelines** para transformações versionadas e parametrizáveis.
- Construção de uma **Feature Store temporal**: as features são recalculadas para cada data de referência histórica, evitando vazamento de dados (*data leakage*) ao simular o que era conhecido até aquele momento — técnica essencial para problemas de séries temporais.
- Validação de modelo com **holdout out-of-time**, mais rigorosa do que um split aleatório tradicional.
- Ciclo de vida de ML completo com **MLflow** (tracking, artefatos, model registry) e **serving via API própria**.

---