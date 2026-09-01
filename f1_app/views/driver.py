"""Tela 2 -- raio-x de um piloto: probabilidade, evolucao e comparacao com o grid."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from f1_app import charts, data, model_meta, theme, ui
from f1_app.scoring import ScoringError, attach_scores


def render() -> None:
    ui.require_config()
    ano, dt_ref = ui.sidebar_period()

    # O titulo da pagina e o nome do piloto, mas o seletor precisa aparecer
    # ABAIXO dele. Containers reservam o lugar antes de sabermos a escolha.
    cabecalho = st.container()
    aviso = st.container()
    seletor = st.container()

    scored = ui.load_scored(dt_ref)
    pilotos = scored["piloto"].tolist()

    with seletor:
        col_piloto, _ = st.columns([1.2, 2.8])
        escolhido = col_piloto.selectbox(
            "Piloto em foco", pilotos, index=0, key="piloto_foco"
        )

    linha = scored.loc[scored["piloto"] == escolhido].iloc[0]
    evento = ui.evento_da_data(ano, dt_ref)
    ate = f"<b>{evento}</b>" if evento else f"<b>{dt_ref.strftime('%d/%m/%Y')}</b>"

    with cabecalho:
        ui.page_intro(
            eyebrow="Raio-x do piloto",
            title=str(linha["piloto"]),
            lede=(
                f"{linha['equipe']} · temporada {ano} · dados ate o {ate}. Por que o "
                "modelo enxerga este piloto assim, e como essa leitura mudou ao longo "
                "do ano."
            ),
            como_ler=[
                "**Probabilidade de titulo** e a saida do modelo para este piloto nesta data.",
                "A **curva de evolucao** nao e interpolada: cada ponto e uma chamada real ao "
                "modelo com as features daquela rodada.",
                "**Onde ele se destaca** compara o piloto com o resto do grid por percentil: "
                "50% e a mediana, ja considerando que em posicao de largada e de chegada "
                "*menor e melhor*.",
                "Troque o piloto no seletor logo abaixo; a corrida de referencia fica na "
                "barra lateral.",
            ],
        )

    with aviso:
        ui.probability_warning(st.session_state.get("_is_probability", True))

    _cabecalho(linha, scored)

    theme.section(
        "Evolucao ao longo da temporada",
        "Como a leitura do modelo mudou a cada data de referencia da temporada.",
    )
    serie_temporada = _season_probabilities(ano)
    if serie_temporada is None or serie_temporada.empty:
        st.info("Nao foi possivel carregar a serie da temporada.")
    else:
        comparar = st.multiselect(
            "Comparar com outros pilotos",
            [p for p in pilotos if p != escolhido],
            max_selections=2,
            help="Ate dois pilotos para contraste na mesma escala.",
        )
        recorte = serie_temporada[serie_temporada["piloto"].isin([escolhido, *comparar])]
        st.altair_chart(charts.trend(recorte), width="stretch")
        st.caption(_variacao(serie_temporada, linha, dt_ref) + " ")
        st.caption(
            "Quedas bruscas costumam vir de uma sequencia ruim de classificacao — "
            "a posicao media de largada e a feature de maior peso do modelo."
        )

    theme.section(
        "Onde ele se destaca",
        "Onde o piloto se posiciona no grid em cada feature de maior peso. "
        "Barra a direita = melhor que a mediana; a esquerda = pior. "
        "Ja considera que, em posicao de largada e chegada, menor e melhor.",
    )
    comparacao = _vs_field_frame(scored, linha)
    if comparacao.empty:
        st.info("Sem features comparaveis nessa data.")
    else:
        st.altair_chart(charts.vs_field(comparacao), width="stretch")

    ui.footer()


def _cabecalho(linha, scored) -> None:
    """Cabecalho imediato: nao depende do reprocessamento da temporada inteira."""
    posicao = int(scored.index[scored["driverid"] == linha["driverid"]][0]) + 1

    col1, col2 = st.columns([1.1, 1.9], gap="large")
    with col1:
        theme.hero(
            "Probabilidade de titulo",
            ui.fmt_pct(float(linha["proba"])),
            f"{posicao}º na leitura do modelo, entre {len(scored)} pilotos",
        )
    with col2:
        a, b, c = st.columns(3)
        a.metric("Posicao no ranking do modelo", f"{posicao}º")
        b.metric(
            "Distancia para o favorito",
            "lidera" if posicao == 1 else ui.fmt_pct(float(scored.iloc[0]["proba"] - linha["proba"])),
            help="Diferenca em pontos percentuais para o piloto mais provavel.",
        )
        c.metric(
            "Fatia do titulo",
            ui.fmt_pct(float(linha["share"])),
            help="Probabilidade normalizada para que todo o grid some 100%.",
        )


def _variacao(serie: pd.DataFrame, linha: pd.Series, dt_ref: pd.Timestamp) -> str:
    """Frase sobre a variacao desde a rodada anterior, se houver historico."""
    historico = serie[
        (serie["driverid"] == linha["driverid"]) & (serie["dt_ref"] < dt_ref)
    ].sort_values("dt_ref")
    if historico.empty:
        return "Esta e a primeira data de referencia da temporada."
    anterior = float(historico.iloc[-1]["proba"])
    return f"Variacao desde a rodada anterior: {(linha['proba'] - anterior) * 100:+.1f} p.p."


@st.cache_data(ttl=15 * 60, show_spinner="Reprocessando a temporada no endpoint...")
def _season_probabilities(ano: int) -> pd.DataFrame | None:
    """Pontua todas as datas de referencia da temporada, uma vez, e guarda em cache."""
    try:
        features = data.load_season(int(ano))
    except data.WarehouseError:
        return None
    if features.empty:
        return None
    try:
        scored, _ = attach_scores(features)
    except ScoringError:
        return None
    return data.display_names(scored)[["dt_ref", "driverid", "piloto", "proba"]]


def _vs_field_frame(scored: pd.DataFrame, linha: pd.Series, n: int = 12) -> pd.DataFrame:
    """Posicao do piloto dentro do grid, feature a feature.

    Usa percentil em vez de diferenca relativa: em contadores como vitorias e
    poles a mediana do grid costuma ser zero, e qualquer razao contra zero
    satura em +100% -- todas as barras ficavam iguais e o grafico nao dizia nada.
    """
    features = model_meta.top_features(n, disponiveis=list(scored.columns))
    total = len(scored)
    registros = []

    for feature in features:
        valores = pd.to_numeric(scored[feature], errors="coerce")
        valor = pd.to_numeric(pd.Series([linha[feature]]), errors="coerce").iloc[0]
        if not np.isfinite(valor) or valores.notna().sum() < 3:
            continue

        # Orienta para "maior = melhor" antes de ranquear.
        orientado = valores * charts.better_direction(feature)
        alvo = valor * charts.better_direction(feature)

        percentil = float((orientado < alvo).sum() + 0.5 * (orientado == alvo).sum()) / total
        posicao = int((orientado > alvo).sum()) + 1

        registros.append(
            {
                "feature": feature,
                "rotulo": model_meta.humanize(feature),
                "valor": valor,
                "mediana": float(valores.median()),
                "posicao": f"{posicao}º de {total}",
                "percentil": percentil,
                "base": 0.5,
            }
        )
    return pd.DataFrame(registros)
