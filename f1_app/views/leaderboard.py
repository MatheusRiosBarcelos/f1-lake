"""Tela 1 -- a corrida pelo titulo na data de referencia escolhida."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from f1_app import charts, data, theme, ui


def render() -> None:
    ui.require_config()
    ano, dt_ref = ui.sidebar_period()
    data_txt = dt_ref.strftime("%d/%m/%Y")
    evento = ui.evento_da_data(ano, dt_ref)
    ate = f"<b>{evento}</b> ({data_txt})" if evento else f"<b>{data_txt}</b>"

    ui.page_intro(
        eyebrow="Corrida pelo titulo",
        title=f"Quem leva o campeonato de {ano}?",
        lede=(
            f"Leitura do modelo logo apos o {ate}. Ele enxerga o historico de cada "
            "piloto ate essa corrida — e so ate ela — e estima a chance de terminar a "
            "temporada como campeao. Trocar a corrida na barra lateral e voltar no "
            "tempo: a leitura passa a ser a que existia naquele ponto do calendario."
        ),
        como_ler=[
            "Cada barra e a probabilidade de **um** piloto ser campeao, avaliada "
            "isoladamente. Por isso a soma passa de 100%.",
            ui.GLOSSARIO,
            "O modelo nao sabe quantas corridas faltam: ele olha ritmo recente de "
            "classificacao e resultado. Por isso, no meio da temporada, ele pode "
            "discordar da tabela de pontos.",
            "Em temporadas encerradas, um aviso compara o favorito do modelo com o "
            "campeao que de fato levou o titulo.",
        ],
    )

    scored = ui.load_scored(dt_ref)
    ui.probability_warning(st.session_state.get("_is_probability", True))
    _contexto_da_temporada(scored, ano)

    _podio(scored)
    _indicadores(scored, ano, dt_ref)

    theme.section(
        "Grid completo",
        "Ordenado pela probabilidade do modelo. Passe o mouse para ver a fatia do titulo.",
    )
    st.altair_chart(charts.leaderboard(scored), width="stretch")
    if len(scored) > 12:
        resto = len(scored) - 12
        maior = float(scored.iloc[12]["proba"])
        st.caption(
            f"Mostrando os 12 primeiros. Os outros {resto} pilotos ficam todos abaixo "
            f"de {ui.fmt_pct(maior)} — a tabela completa esta logo abaixo."
        )

    _tabela(scored, ano, dt_ref)
    ui.footer()


def _podio(scored: pd.DataFrame) -> None:
    """Os tres favoritos em destaque -- a resposta que a maioria veio buscar."""
    colunas = st.columns(3, gap="medium")
    for posicao, (coluna, (_, linha)) in enumerate(zip(colunas, scored.head(3).iterrows()), 1):
        with coluna:
            theme.podium_card(
                posicao=posicao,
                nome=str(linha["piloto"]),
                equipe=str(linha["equipe"]),
                valor=ui.fmt_pct(float(linha["proba"])),
                sub=f"{ui.fmt_pct(float(linha['share']))} do titulo em disputa",
            )


def _indicadores(scored: pd.DataFrame, ano: int, dt_ref: pd.Timestamp) -> None:
    lider = scored.iloc[0]
    vice = scored.iloc[1] if len(scored) > 1 else None

    a, b, c, d = st.columns(4)
    a.metric("Pilotos avaliados", len(scored))
    b.metric(
        "Candidatos reais",
        int((scored["proba"] >= 0.10).sum()),
        help="Pilotos com 10% ou mais de probabilidade.",
    )
    c.metric(
        "Vantagem do favorito",
        "—" if vice is None else f"{(lider['proba'] - vice['proba']) * 100:.1f} p.p.",
        help=f"Distancia de {lider['piloto']} para o segundo colocado do modelo.",
    )
    d.metric(
        "Concentracao",
        ui.fmt_pct(float(lider["share"]), 0),
        help="Fatia do favorito quando as probabilidades sao normalizadas para somar 100%.",
    )


def _tabela(scored: pd.DataFrame, ano: int, dt_ref: pd.Timestamp) -> None:
    with st.expander("Ver tabela completa e baixar os numeros"):
        standings = data.load_standings(ano, dt_ref)
        tabela = scored.merge(standings, on="driverid", how="left")
        tabela.insert(0, "#", range(1, len(tabela) + 1))
        colunas = {
            "#": "#",
            "piloto": "Piloto",
            "equipe": "Equipe",
            "proba": "Probabilidade",
            "share": "Fatia do titulo",
            "pontos": "Pontos ate a data",
        }
        exibir = tabela[[c for c in colunas if c in tabela.columns]].rename(columns=colunas)

        # As colunas guardam fracao (0-1). O printf `%%` do column_config e apenas
        # um sinal de porcentagem literal -- nao reescala. Convertemos aqui, senao
        # 0,582 apareceria como "0.6%".
        for coluna in ("Probabilidade", "Fatia do titulo"):
            if coluna in exibir.columns:
                exibir[coluna] = exibir[coluna] * 100

        st.dataframe(
            exibir,
            hide_index=True,
            width="stretch",
            column_config={
                "Probabilidade": st.column_config.NumberColumn(
                    format="%.1f%%", help="Chance de este piloto ser campeao, avaliado isoladamente."
                ),
                "Fatia do titulo": st.column_config.NumberColumn(
                    format="%.1f%%", help="Probabilidade normalizada para que o grid some 100%."
                ),
                "Pontos ate a data": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        st.caption(
            "*Pontos ate a data* vem da camada bronze (resultados reais) e serve de "
            "contraponto: e o campeonato como ele esta, nao como o modelo o le."
        )
        # No CSV a unidade some da celula, entao ela vai no cabecalho.
        csv = exibir.rename(
            columns={"Probabilidade": "Probabilidade (%)", "Fatia do titulo": "Fatia do titulo (%)"}
        )
        st.download_button(
            "Baixar CSV",
            csv.to_csv(index=False).encode("utf-8"),
            file_name=f"f1_probabilidades_{dt_ref.date()}.csv",
            mime="text/csv",
        )


def _contexto_da_temporada(scored: pd.DataFrame, ano: int) -> None:
    """Confere contra o campeao real -- mas so quando a temporada ja acabou.

    Para a temporada em curso, `flChampion` vem de um ROW_NUMBER sobre os pontos
    acumulados: marca o LIDER ate a data, nao um campeao confirmado. Tratar isso
    como verdade historica seria anunciar um campeao que ainda nao existe.
    """
    if "flchampion" not in scored.columns or scored["flchampion"].sum() == 0:
        return

    marcado = scored.loc[scored["flchampion"] == 1].iloc[0]
    posicao = int(scored.index[scored["driverid"] == marcado["driverid"]][0]) + 1
    em_andamento = ano >= dt.date.today().year

    if em_andamento:
        st.info(
            f"**Temporada em andamento.** O lider do campeonato ate essa data e "
            f"**{marcado['piloto']}**, que o modelo coloca em {posicao}º "
            f"({ui.fmt_pct(float(marcado['proba']))}). Nada aqui e resultado final.",
            icon="🏁",
        )
    elif posicao == 1:
        st.success(
            f"**Temporada encerrada.** O campeao foi **{marcado['piloto']}** — "
            "e o modelo o coloca em 1º nessa data.",
            icon="✅",
        )
    else:
        st.info(
            f"**Temporada encerrada.** O campeao foi **{marcado['piloto']}**, "
            f"que o modelo coloca em {posicao}º nessa data "
            f"({ui.fmt_pct(float(marcado['proba']))}).",
            icon="📌",
        )
