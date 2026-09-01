"""Graficos Altair. Forma escolhida pelo trabalho do dado; cor por ultimo."""

from __future__ import annotations

import altair as alt
import pandas as pd

from f1_app import theme

# Features em que MENOR e melhor (posicoes). O resto: maior e melhor.
_LOWER_IS_BETTER = ("avg_gridposition", "avg_position")


def better_direction(feature: str) -> int:
    return -1 if feature.startswith(_LOWER_IS_BETTER) else 1


def leaderboard(df: pd.DataFrame, height_per_bar: int = 26, topo: int = 12) -> alt.Chart:
    """Magnitude, baixo -> alto: barras horizontais com rampa sequencial de um tom.

    Corta a cauda: uma dezena de barras em 0,0% nao carrega informacao, so ruido.
    A tabela completa continua disponivel na propria tela.
    """
    df = df.head(topo).copy()
    df["proba_txt"] = df["proba"].map(lambda v: f"{v * 100:.1f}%".replace(".", ","))
    df["share_txt"] = df["share"].map(lambda v: f"{v * 100:.1f}%".replace(".", ","))
    base = alt.Chart(df).encode(
        y=alt.Y(
            "piloto:N",
            sort=alt.EncodingSortField("proba", order="descending"),
            title=None,
            axis=alt.Axis(labelLimit=200),
            scale=alt.Scale(paddingInner=0.28),
        ),
        tooltip=[
            alt.Tooltip("piloto:N", title="Piloto"),
            alt.Tooltip("equipe:N", title="Equipe"),
            alt.Tooltip("proba_txt:N", title="Probabilidade"),
            alt.Tooltip("share_txt:N", title="Fatia do titulo"),
        ],
    )

    barras = base.mark_bar(cornerRadiusEnd=4, height=14).encode(
        x=alt.X(
            "proba:Q",
            title="Probabilidade de ser campeao",
            axis=alt.Axis(format="%", tickCount=5),
            scale=alt.Scale(domain=[0, max(1e-6, float(df["proba"].max()) * 1.18)]),
        ),
        color=alt.Color(
            "proba:Q",
            scale=alt.Scale(range=theme.SEQUENTIAL),
            legend=None,
        ),
    )

    rotulos = base.mark_text(
        align="left", dx=6, fontSize=11, color=theme.TEXT_SECONDARY
    ).encode(x=alt.X("proba:Q"), text=alt.Text("proba_txt:N"))

    return (barras + rotulos).properties(
        height=max(180, height_per_bar * len(df)), width="container"
    )


def trend(df: pd.DataFrame, y: str = "proba") -> alt.Chart:
    """Evolucao no tempo. 1 serie -> tom unico sem legenda; 2+ -> categorico + legenda."""
    series = sorted(df["piloto"].unique())
    multi = len(series) > 1

    color = (
        alt.Color(
            "piloto:N",
            title=None,
            scale=alt.Scale(
                domain=series,
                range=[theme.ACCENT, theme.ACCENT_2, theme.POSITIVE][: len(series)],
            ),
        )
        if multi
        else alt.value(theme.ACCENT)
    )

    base = alt.Chart(df).encode(
        x=alt.X("dt_ref:T", title=None, axis=alt.Axis(format="%d/%m", tickCount=7)),
        y=alt.Y(f"{y}:Q", title="Probabilidade", axis=alt.Axis(format="%")),
        color=color,
    )

    linha = base.mark_line(strokeWidth=2, point=False)
    pontos = base.mark_point(size=60, filled=True, stroke=theme.SURFACE, strokeWidth=2).encode(
        tooltip=[
            alt.Tooltip("piloto:N", title="Piloto"),
            alt.Tooltip("dt_ref:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip(f"{y}:Q", title="Probabilidade", format=".1%"),
        ]
    )

    ultimo = df.sort_values("dt_ref").groupby("piloto", as_index=False).tail(1)
    rotulos = (
        alt.Chart(ultimo)
        .mark_text(align="left", dx=8, fontSize=11, color=theme.TEXT_SECONDARY)
        .encode(x="dt_ref:T", y=f"{y}:Q", text="piloto:N")
    )

    grafico = linha + pontos + rotulos if multi else linha + pontos
    return grafico.properties(height=300, width="container")


def vs_field(df: pd.DataFrame) -> alt.Chart:
    """Posicao no grid: barra saindo da mediana (percentil 50) ate o percentil do piloto.

    Percentil em vez de diferenca relativa: em contadores cuja mediana e zero
    (vitorias, poles) qualquer razao satura e todas as barras ficam iguais.
    """
    barras = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=13)
        .encode(
            x=alt.X(
                "percentil:Q",
                title="Percentil no grid (mediana = 50%)",
                axis=alt.Axis(format=".0%", tickCount=5),
                scale=alt.Scale(domain=[0, 1]),
            ),
            x2=alt.X2("base:Q"),
            y=alt.Y(
                "rotulo:N",
                sort=alt.EncodingSortField("percentil", order="descending"),
                title=None,
                axis=alt.Axis(labelLimit=280),
                scale=alt.Scale(paddingInner=0.3),
            ),
            color=alt.condition(
                alt.datum.percentil >= 0.5, alt.value(theme.ACCENT), alt.value(theme.NEGATIVE)
            ),
            tooltip=[
                alt.Tooltip("rotulo:N", title="Feature"),
                alt.Tooltip("posicao:N", title="Posicao no grid"),
                alt.Tooltip("percentil:Q", title="Percentil", format=".0%"),
                alt.Tooltip("valor:Q", title="Valor do piloto", format=".2f"),
                alt.Tooltip("mediana:Q", title="Mediana do grid", format=".2f"),
            ],
        )
    )
    mediana = (
        alt.Chart(pd.DataFrame({"x": [0.5]}))
        .mark_rule(color=theme.TEXT_MUTED, strokeWidth=1, strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    return (barras + mediana).properties(height=max(200, 26 * len(df)), width="container")


def importance(df: pd.DataFrame) -> alt.Chart:
    """Magnitude -> barras horizontais, rampa sequencial."""
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=13)
        .encode(
            x=alt.X("importancia:Q", title="Importancia (Gini)",
                    axis=alt.Axis(format=".1%", tickCount=5)),
            y=alt.Y("feature:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=300), scale=alt.Scale(paddingInner=0.3)),
            color=alt.Color("importancia:Q", scale=alt.Scale(range=theme.SEQUENTIAL), legend=None),
            tooltip=[
                alt.Tooltip("feature:N", title="Feature"),
                alt.Tooltip("importancia:Q", title="Importancia", format=".3%"),
            ],
        )
        .properties(height=max(200, 24 * len(df)), width="container")
    )


def before_after(baseline: float, simulado: float) -> alt.Chart:
    """Antes -> depois de um item: duas barras, duas fatias categoricas, rotuladas."""
    df = pd.DataFrame(
        {"cenario": ["Real", "Simulado"], "proba": [baseline, simulado]}
    )
    base = alt.Chart(df).encode(
        y=alt.Y("cenario:N", title=None, sort=["Real", "Simulado"],
                scale=alt.Scale(paddingInner=0.35)),
        x=alt.X("proba:Q", title=None, axis=alt.Axis(format="%", tickCount=4),
                scale=alt.Scale(domain=[0, max(0.02, baseline, simulado) * 1.25])),
    )
    barras = base.mark_bar(cornerRadiusEnd=4, height=22).encode(
        color=alt.Color("cenario:N", legend=None,
                        scale=alt.Scale(domain=["Real", "Simulado"],
                                        range=[theme.MUTED_MARK, theme.ACCENT])),
        tooltip=[alt.Tooltip("cenario:N", title="Cenario"),
                 alt.Tooltip("proba:Q", title="Probabilidade", format=".1%")],
    )
    rotulos = base.mark_text(align="left", dx=6, fontSize=12,
                             color=theme.TEXT_SECONDARY).encode(
        text=alt.Text("proba:Q", format=".1%")
    )
    return (barras + rotulos).properties(height=120, width="container")
