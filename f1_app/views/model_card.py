"""Tela 4 -- ficha do modelo e da arquitetura. Funciona sem credenciais."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from f1_app import charts, model_meta, theme, ui
from f1_app.config import get_settings

ARQUITETURA = """
| Camada | Onde roda | O que faz |
|---|---|---|
| Ingestao | Local (`main.py`, loop de 6h) | FastF1 -> Parquet -> bucket S3 |
| Bronze | Databricks (streaming table) | `read_files` do S3 em `lakehouse.bronze.f1_results` |
| Silver | Databricks (materialized views) | Feature store por piloto e data de referencia, em janelas de 10/20/40 corridas e carreira |
| Gold | Databricks | ABT `abt_f1_drivers_champion` = feature store + flag de campeao |
| Modelo | Databricks + MLflow | RandomForest (`min_samples_leaf=50`, 500 arvores) com imputacao arbitraria (-10000) |
| Serving | Databricks Model Serving | Endpoint REST consumido por este app |
"""


def render() -> None:
    ui.page_intro(
        eyebrow="Sobre o modelo",
        title="Como esta previsao e feita",
        lede=(
            "O que o modelo aprendeu, quanto se pode confiar nele e por onde o dado "
            "passa antes de virar uma probabilidade na tela. Esta pagina funciona sem "
            "credenciais — e a ficha tecnica do projeto."
        ),
        como_ler=[
            "**ROC AUC** mede a capacidade de ordenar: 1,0 e perfeito, 0,5 e sorteio. "
            "O numero que importa e o *out-of-time*.",
            "**Importancia** mostra o quanto cada variavel reduz a incerteza do modelo — "
            "e uma medida de uso, nao de causa.",
        ],
    )

    theme.section("Desempenho", "ROC AUC em cada conjunto de validacao.")
    colunas = st.columns(len(model_meta.METRICS))
    for coluna, (nome, valor) in zip(colunas, model_meta.METRICS.items()):
        coluna.metric(nome, f"{valor:.4f}".rstrip("0").rstrip("."))

    st.info(
        "A distancia entre o AUC de teste (~1,0) e o out-of-time de 2025 (0,955) e o "
        "numero honesto: o recorte temporal e a unica validacao que respeita a ordem "
        "dos eventos. O split aleatorio deixa linhas do mesmo piloto/temporada dos dois "
        "lados, o que infla a metrica.",
        icon="⚠️",
    )

    esquerda, direita = st.columns([1, 1], gap="large")  # ROC + explicacao do alvo
    with esquerda:
        if model_meta.ROC_CURVE.exists():
            st.image(str(model_meta.ROC_CURVE), caption="Curva ROC (artefato do MLflow)")
    with direita:
        st.markdown("**Como o alvo e construido**")
        st.markdown(
            "- `flChampion` marca o piloto com mais pontos somados (corrida + sprint) na temporada.\n"
            "- Cada linha da ABT e um par piloto x data de referencia: as features so "
            "enxergam corridas ate aquela data.\n"
            "- O treino descarta as 5 ultimas rodadas de cada ano nos conjuntos de "
            "treino/teste, onde o campeao ja e praticamente conhecido."
        )

    theme.section(
        "O que pesa na decisao",
        "Importancia de cada variavel no RandomForest, exportada do MLflow.",
    )
    importancias = model_meta.feature_importances()
    if importancias.empty:
        st.info("Arquivo `ml_champion/feature_importances.md` nao encontrado.")
    else:
        top_n = st.slider("Quantas features mostrar", 5, 40, 20)
        topo = importancias.head(top_n).copy()
        topo["feature"] = topo["rotulo"]
        st.altair_chart(charts.importance(topo), width="stretch")
        st.caption(
            "Posicao media de largada nas ultimas 10-40 corridas domina: no F1 moderno, "
            "ritmo de classificacao recente e o melhor proxy de titulo."
        )
        with st.expander("Tabela completa de importancias"):
            st.dataframe(
                importancias.rename(
                    columns={"feature": "Feature", "importancia": "Importancia", "rotulo": "Descricao"}
                ),
                hide_index=True,
                width="stretch",
            )

    theme.section("Arquitetura do pipeline", "Onde cada etapa roda.")
    st.markdown(ARQUITETURA)

    theme.section("Conexao", "Para onde este app esta apontando agora.")
    cfg = get_settings()
    st.dataframe(
        pd.DataFrame(
            [
                {"Item": "Workspace", "Valor": cfg.server_hostname},
                {"Item": "Endpoint de serving", "Valor": cfg.endpoint_url},
                {"Item": "SQL Warehouse", "Valor": cfg.http_path or "nao configurado"},
                {"Item": "Tabela ABT", "Valor": cfg.abt_table},
                {"Item": "Token", "Valor": "configurado" if cfg.token else "ausente"},
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    ui.footer()
