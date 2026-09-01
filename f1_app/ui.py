"""Componentes compartilhados entre as telas."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from f1_app import data, theme
from f1_app.config import get_settings

SETUP_MD = """
### Configuracao pendente

Esta tela precisa de acesso ao lakehouse e ao endpoint de serving.

**Rodando local** -- crie um `.env` na raiz do projeto:

```bash
cp .env.example .env
```

```dotenv
DATABRICKS_TOKEN=dapi...                        # PAT com CAN QUERY no endpoint
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxxx  # SQL Warehouse > Connection details
```

**No Streamlit Community Cloud** -- o `.env` nao sobe para o repositorio; cole os
mesmos valores em **App settings -> Secrets**, em formato TOML:

```toml
DATABRICKS_TOKEN = "dapi..."
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/xxxxx"
```

A pagina **Sobre o modelo** funciona sem credenciais.
"""


def require_config() -> None:
    cfg = get_settings()
    if cfg.has_warehouse and cfg.has_endpoint:
        return
    st.title("F1 Champion Predictor")
    st.warning("Faltando: " + ", ".join(cfg.missing))
    st.markdown(SETUP_MD)
    st.stop()


def page_intro(eyebrow: str, title: str, lede: str, como_ler: list[str] | None = None) -> None:
    """Cabecalho de tela: o que e, em uma frase, mais um guia de leitura opcional."""
    theme.page_header(eyebrow, title, lede, como_ler)


def sidebar_period() -> tuple[int, pd.Timestamp]:
    """Seletor de temporada + data de referencia. Devolve (ano, dt_ref)."""
    with st.sidebar:
        st.markdown('<div class="f1-sidebar-label">Recorte</div>', unsafe_allow_html=True)
        try:
            refs = data.list_dt_refs()
        except data.WarehouseError as err:
            st.error(f"Sem conexao com o SQL Warehouse.\n\n{err}")
            dica = explain_warehouse_error(err)
            if dica:
                st.info(dica)
            st.stop()

        if refs.empty:
            st.error("A ABT nao retornou nenhuma data de referencia.")
            st.stop()

        anos = sorted(refs["year"].unique(), reverse=True)
        ano = st.selectbox("Temporada", anos, index=0, key="periodo_ano")

        datas = refs.loc[refs["year"] == ano, "dt_ref"].sort_values(ascending=False)
        eventos = data.event_info(ano)

        def rotulo(d) -> str:
            quando = pd.Timestamp(d)
            info = eventos.get(quando)
            return f"{info['lista']} · {quando:%d/%m}" if info else quando.strftime("%d/%m/%Y")

        dt_ref = st.selectbox(
            "Ultima corrida considerada",
            datas,
            index=0,
            format_func=rotulo,
            key="periodo_dt",
        )
        info = eventos.get(pd.Timestamp(dt_ref))
        quando = pd.Timestamp(dt_ref).strftime("%d/%m/%Y")
        st.caption(
            (f"Historico ate o {info['prosa']}, em {quando}. " if info
             else f"Historico ate {quando}. ")
            + f"{len(datas)} sessoes disponiveis em {ano} — mudar a corrida e viajar no "
            "tempo, nao filtrar."
        )

        st.divider()
        with st.expander("Como funciona"):
            st.markdown(
                "1. **Coleta** — resultados de corrida e sprint via FastF1, "
                "enviados para o S3.\n"
                "2. **Lakehouse** — Databricks organiza em bronze → silver → gold. "
                "A camada silver monta uma *feature store* que, para cada data, "
                "recalcula o historico de cada piloto em janelas de 10, 20 e 40 "
                "corridas e carreira inteira.\n"
                "3. **Modelo** — um RandomForest le essas ~172 features e devolve a "
                "probabilidade de o piloto terminar a temporada como campeao.\n"
                "4. **Este app** — busca a linha do piloto no lakehouse e chama o "
                "endpoint de serving do Databricks a cada consulta."
            )

        if st.button("Limpar cache", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption("Os dados ficam em cache por 30 min. Limpe apos atualizar o lake.")

    return int(ano), pd.Timestamp(dt_ref)


def explain_warehouse_error(err: Exception) -> str | None:
    """Traduz os erros mais comuns do driver para uma acao concreta."""
    msg = str(err).lower()

    if "scopes" in msg and "sql" in msg:
        return (
            "**O token nao alcanca o escopo `sql`.** Nesta workspace os PATs sao emitidos "
            "com escopos restritos -- um token gerado a partir da tela do serving endpoint "
            "costuma cobrir so `serving-endpoints`. Gere um token geral em "
            "**Settings > Developer > Access tokens > Generate new token** e teste com "
            "`python scripts/check_auth.py`, que mostra o mapa de escopos efetivos."
        )
    if "invalid access token" in msg or "401" in msg or "unauthorized" in msg:
        return (
            "Token invalido ou expirado. Gere outro em **Settings > Developer > "
            "Access tokens** e atualize o `.env`. Diagnostico: `python scripts/check_auth.py`."
        )
    if "not found" in msg and "warehouse" in msg:
        return (
            "O `DATABRICKS_HTTP_PATH` nao aponta para um warehouse existente. "
            "Confira em **SQL > SQL Warehouses > Connection details**, ou rode "
            "`python scripts/check_auth.py` para listar os caminhos validos."
        )
    if "table_or_view_not_found" in msg or "table or view not found" in msg:
        return (
            "A tabela da ABT nao foi encontrada. Ajuste `ABT_TABLE` no `.env` para o "
            "nome real no Unity Catalog."
        )
    return None


def evento_da_data(ano: int, dt_ref, forma: str = "prosa") -> str:
    """Rotulo do GP daquela data. `forma`: "prosa" (frases) ou "lista" (seletor)."""
    info = data.event_info(int(ano)).get(pd.Timestamp(dt_ref))
    return info[forma] if info else ""


def probability_warning(is_probability: bool) -> None:
    """O flavor sklearn padrao serve `predict` (classe 0/1), nao a probabilidade."""
    if is_probability:
        return
    st.error(
        "**O endpoint esta devolvendo classe (0/1), nao probabilidade** -- o ranking "
        "abaixo so tem 0% e 100%.\n\n"
        "A causa e o `mlflow.sklearn.log_model` servir `predict()` por padrao. "
        "A correcao e uma linha: `pyfunc_predict_fn=\"predict_proba\"`. "
        "Rode `ml_champion/serve_proba.py` num notebook do Databricks (registra uma "
        "nova versao de `lakehouse.gold.f1_champion_model` sem retreinar) e aponte "
        "**Serving > f1-champions > Edit** para ela."
    )


def load_scored(dt_ref) -> pd.DataFrame:
    """Features da data + probabilidade + nomes, ordenado por probabilidade."""
    from f1_app.scoring import ScoringError, attach_scores

    try:
        features = data.load_features(dt_ref)
    except data.WarehouseError as err:
        st.error(f"Erro ao ler a ABT: {err}")
        st.stop()

    if features.empty:
        st.warning("Nenhum piloto encontrado nessa data de referencia.")
        st.stop()

    try:
        scored, is_prob = attach_scores(features)
    except ScoringError as err:
        st.error(f"Erro ao pontuar no endpoint:\n\n{err}")
        st.stop()

    st.session_state["_is_probability"] = is_prob
    scored = data.display_names(scored)
    scored["share"] = scored["proba"] / scored["proba"].sum() if scored["proba"].sum() else 0.0
    return scored.sort_values("proba", ascending=False).reset_index(drop=True)


GLOSSARIO = (
    "**Probabilidade** e a leitura do modelo para aquele piloto isoladamente — por "
    "isso as probabilidades nao somam 100%. **Fatia do titulo** normaliza todas para "
    "somar 100%, respondendo \"de quem e o campeonato?\" em vez de \"quao forte esta "
    "este piloto?\"."
)


def fmt_pct(value: float, casas: int = 1) -> str:
    return f"{value * 100:.{casas}f}%".replace(".", ",")


def footer() -> None:
    st.divider()
    st.markdown(
        '<div class="f1-muted">'
        "FastF1 → S3 → Databricks (bronze · silver · gold) → RandomForest servido em "
        "Databricks Model Serving. Probabilidades sao estimativas do modelo, nao "
        "prognosticos oficiais."
        "</div>",
        unsafe_allow_html=True,
    )
