"""Tela 3 -- simulador: mexer nas features principais e ver a probabilidade reagir."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from f1_app import charts, model_meta, theme, ui
from f1_app.scoring import ScoringError, attach_scores


def render() -> None:
    ui.require_config()
    ano, dt_ref = ui.sidebar_period()

    # Mesma logica do raio-x: o lede cita o piloto escolhido, entao o cabecalho
    # e reservado antes e preenchido depois que o seletor roda.
    cabecalho = st.container()
    aviso = st.container()
    seletor = st.container()

    scored = ui.load_scored(dt_ref)
    pilotos = scored["piloto"].tolist()

    with seletor:
        col_piloto, col_n, _ = st.columns([1.2, 1.4, 1.4])
        escolhido = col_piloto.selectbox("Piloto base", pilotos, index=0, key="piloto_sim")
        n_features = col_n.slider(
            "Quantas features ajustar",
            4, 16, 8, key="n_sim",
            help="As features entram na ordem de importancia para o modelo.",
        )

    base_row = scored.loc[scored["piloto"] == escolhido].iloc[0]
    baseline = float(base_row["proba"])

    with cabecalho:
        ui.page_intro(
            eyebrow="Simulador",
            title="E se o piloto tivesse rendido diferente?",
            lede=(
                f"Parte do cenario real de <b>{escolhido}</b> apos o "
                f"<b>{ui.evento_da_data(ano, dt_ref) or dt_ref.strftime('%d/%m/%Y')}</b> e "
                "deixa voce mexer nas variaveis que mais pesam na decisao do modelo. Cada "
                "ajuste reenvia a linha inteira ao endpoint e mostra a probabilidade "
                "recalculada."
            ),
            como_ler=[
                "Os sliders comecam nos **valores reais** do piloto. Sem mexer em nada, o "
                "cenario simulado reproduz exatamente a probabilidade real.",
                "Cada slider diz no *tooltip* se **maior e melhor** ou **menor e melhor** — "
                "em posicao de largada, por exemplo, cair de 8º para 3º e uma melhora.",
                "As features estao ordenadas pela importancia no modelo: as primeiras "
                "movem o resultado muito mais que as ultimas.",
                "**Posicao no ranking** recalcula onde o piloto ficaria no grid com o "
                "cenario simulado, mantendo os demais como estao.",
            ],
        )

    with aviso:
        ui.probability_warning(st.session_state.get("_is_probability", True))

    features = model_meta.top_features(n_features, disponiveis=list(scored.columns))
    if not features:
        st.warning("Nenhuma feature ajustavel encontrada na ABT.")
        return

    if st.button("Restaurar valores reais"):
        for feature in features:
            st.session_state.pop(f"sim_{feature}", None)
        st.rerun()

    col_controles, col_resultado = st.columns([1.25, 1], gap="large")

    with col_controles:
        theme.section("Ajuste o desempenho", "Ordenado pela importancia no modelo.")
        ajustes, alterados = _sliders(scored, base_row, features)

    cenario = base_row.to_frame().T.copy()
    for feature, valor in ajustes.items():
        cenario[feature] = valor

    with col_resultado:
        theme.section("Resultado", "Recalculado no endpoint a cada mudanca.")
        _resultado(cenario, baseline, scored, escolhido, alterados)

    ui.footer()


def _sliders(
    scored: pd.DataFrame, base_row: pd.Series, features: list[str]
) -> tuple[dict, list[tuple[str, float, float]]]:
    """Sliders das features principais.

    Um slider intocado devolve o valor ORIGINAL (sem arredondamento, NaN
    inclusive), para que o cenario sem ajustes reproduza exatamente a linha real.
    """
    ajustes: dict = {}
    alterados: list[tuple[str, float, float]] = []

    for feature in features:
        coluna = pd.to_numeric(scored[feature], errors="coerce").dropna()
        original = pd.to_numeric(pd.Series([base_row[feature]]), errors="coerce").iloc[0]
        atual = original
        if not np.isfinite(atual):
            atual = float(coluna.median()) if not coluna.empty else 0.0

        lo = float(min(coluna.min(), atual)) if not coluna.empty else float(atual)
        hi = float(max(coluna.max(), atual)) if not coluna.empty else float(atual) + 1
        margem = max((hi - lo) * 0.25, 1.0)
        lo, hi = lo - margem, hi + margem
        if feature.startswith(("avg_gridposition", "avg_position")):
            lo = max(lo, 1.0)

        inteiro = feature.startswith("qtde") or feature.startswith("qtd_")
        passo = 1.0 if inteiro else round(max((hi - lo) / 100, 0.01), 2)

        sentido = "menor e melhor" if charts.better_direction(feature) < 0 else "maior e melhor"
        padrao = round(float(atual), 2)
        valor = st.slider(
            model_meta.humanize(feature),
            min_value=round(lo, 2),
            max_value=round(hi, 2),
            value=padrao,
            step=passo,
            key=f"sim_{feature}",
            help=f"{feature} · {sentido} · valor real: {atual:.2f}",
        )
        if valor == padrao:
            ajustes[feature] = original
        else:
            ajustes[feature] = valor
            alterados.append((feature, float(atual), float(valor)))

    return ajustes, alterados


def _resultado(
    cenario: pd.DataFrame,
    baseline: float,
    scored: pd.DataFrame,
    escolhido: str,
    alterados: list[tuple[str, float, float]],
) -> None:
    try:
        simulado_df, _ = attach_scores(cenario)
    except ScoringError as err:
        st.error(f"Erro ao pontuar o cenario:\n\n{err}")
        return

    simulado = float(simulado_df["proba"].iloc[0])
    delta = simulado - baseline

    theme.hero(
        "Probabilidade simulada",
        ui.fmt_pct(simulado),
        f"{delta * 100:+.1f} p.p. vs. cenario real ({ui.fmt_pct(baseline)})",
    )
    st.altair_chart(charts.before_after(baseline, simulado), width="stretch")

    ranking = scored[scored["piloto"] != escolhido]["proba"].tolist() + [simulado]
    nova_pos = sorted(ranking, reverse=True).index(simulado) + 1
    pos_real = int(scored.index[scored["piloto"] == escolhido][0]) + 1
    st.metric(
        "Posicao no ranking do modelo",
        f"{nova_pos}º",
        delta=f"{pos_real - nova_pos:+d} posicoes" if nova_pos != pos_real else None,
        delta_color="normal",
    )

    if alterados:
        st.markdown("**O que foi alterado**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Feature": model_meta.humanize(f), "Real": r, "Simulado": s}
                    for f, r, s in alterados
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption(
            "Nenhum ajuste aplicado ainda — mova um slider ao lado e o numero acima "
            "se move junto."
        )
