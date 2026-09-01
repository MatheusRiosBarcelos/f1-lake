"""Faz o serving endpoint devolver PROBABILIDADE em vez de classe (0/1).

Por padrao o flavor `mlflow.sklearn` serve `predict()`, que devolve a classe --
inutil para ranquear pilotos. O parametro `pyfunc_predict_fn` troca a funcao
exposta pelo pyfunc para `predict_proba`, SEM retreinar nada.

Cole num notebook do Databricks (precisa da sessao `spark` e do Unity Catalog).
Depois aponte o endpoint `f1-champions` para a nova versao.

IMPORTANTE -- primeira celula do notebook, antes de qualquer import:

    %pip install feature-engine
    dbutils.library.restartPython()

O pipeline treinado embute `feature_engine.imputation.ArbitraryNumberImputer`.
Sem a lib instalada, o `cloudpickle.load` falha com ModuleNotFoundError ao
desempacotar o modelo -- a classe precisa ser importavel para o unpickle.
"""

import mlflow
import mlflow.sklearn

mlflow.set_registry_uri("databricks-uc")

# Valores reais do endpoint `f1-champions` (lidos via API em 01/09/2026).
MODELO_UC = "lakehouse.gold.f1_champion_model"
VERSAO_ATUAL = 1
ABT = "lakehouse.gold.abt_f1_drivers_champion"

NAO_FEATURES = {"dt_ref", "driverid", "flchampion"}


def exemplo_de_entrada(n: int = 5):
    """Algumas linhas da ABT, so com as colunas que o modelo recebe."""
    df = spark.table(ABT).limit(n).toPandas()  # noqa: F821 -- `spark` vem do notebook
    return df[[c for c in df.columns if c.lower() not in NAO_FEATURES]]


def republicar(versao: int = VERSAO_ATUAL, modelo: str = MODELO_UC):
    """Recarrega o pipeline treinado e registra uma nova versao expondo `predict_proba`."""
    pipeline = mlflow.sklearn.load_model(f"models:/{modelo}/{versao}")

    with mlflow.start_run(run_name="serve_proba"):
        info = mlflow.sklearn.log_model(
            pipeline,
            name="model",
            pyfunc_predict_fn="predict_proba",   # <- a correcao inteira
            input_example=exemplo_de_entrada(),
            registered_model_name=modelo,        # vira a versao seguinte do mesmo modelo
            # Garante que a nova versao declare a dependencia que o pipeline usa;
            # o requirements.txt da v1 nao a listava.
            extra_pip_requirements=["feature-engine"],
        )

    print("Registrado:", info.model_uri)
    print(f"Agora: Serving > f1-champions > Edit > servir a nova versao de {modelo}.")
    return info


if __name__ == "__main__":
    republicar()

# A saida passa a ser [prob_classe_0, prob_classe_1] por linha. O app ja lê a
# ultima posicao (f1_app/scoring.py::_parse), entao nada muda no Streamlit.
