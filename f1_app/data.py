"""Leitura do lakehouse via Databricks SQL Warehouse."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from f1_app.config import get_settings

TTL = 30 * 60  # 30 min


class WarehouseError(RuntimeError):
    """Falha ao consultar o SQL Warehouse."""


def _connect():
    from databricks import sql

    cfg = get_settings()
    if not cfg.has_warehouse:
        raise WarehouseError(
            "Credenciais ausentes: " + ", ".join(cfg.missing)
        )
    return sql.connect(
        server_hostname=cfg.server_hostname,
        http_path=cfg.http_path,
        access_token=cfg.token,
    )


def _run(query: str) -> pd.DataFrame:
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(query)
            try:
                df = cur.fetchall_arrow().to_pandas()
            except Exception:
                rows = cur.fetchall()
                cols = [c[0] for c in cur.description]
                df = pd.DataFrame(rows, columns=cols)
    except WarehouseError:
        raise
    except Exception as err:  # noqa: BLE001 -- erro do driver vira mensagem de UI
        raise WarehouseError(str(err)) from err
    df.columns = [c.lower() for c in df.columns]
    return df


def _safe_date(value) -> str:
    """Valida a data antes de interpolar na query (vem sempre de um seletor)."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return dt.date.fromisoformat(str(value)[:10]).isoformat()


@st.cache_data(ttl=TTL, show_spinner="Consultando o lakehouse...")
def list_dt_refs() -> pd.DataFrame:
    """Datas de referencia disponiveis na ABT, com o ano derivado."""
    cfg = get_settings()
    df = _run(
        f"SELECT DISTINCT dt_ref FROM {cfg.abt_table} ORDER BY dt_ref DESC"
    )
    df["dt_ref"] = pd.to_datetime(df["dt_ref"])
    df["year"] = df["dt_ref"].dt.year
    return df


@st.cache_data(ttl=TTL, show_spinner="Carregando features dos pilotos...")
def load_features(dt_ref) -> pd.DataFrame:
    """Uma linha por piloto na data de referencia -- a entrada do modelo."""
    cfg = get_settings()
    date_str = _safe_date(dt_ref)
    df = _run(
        f"SELECT * FROM {cfg.abt_table} WHERE dt_ref = date('{date_str}')"
    )
    return _normalize_abt(df)


@st.cache_data(ttl=TTL, show_spinner="Carregando temporada...")
def load_season(year: int) -> pd.DataFrame:
    """Todas as datas de referencia de uma temporada (para a curva de evolucao)."""
    cfg = get_settings()
    year = int(year)
    df = _run(
        f"SELECT * FROM {cfg.abt_table} "
        f"WHERE dt_ref >= date('{year}-01-01') AND dt_ref < date('{year + 1}-01-01')"
    )
    return _normalize_abt(df)


def _normalize_abt(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["dt_ref"] = pd.to_datetime(df["dt_ref"])
    df["driverid"] = df["driverid"].astype(str)
    if "flchampion" in df.columns:
        df["flchampion"] = pd.to_numeric(df["flchampion"], errors="coerce").fillna(0).astype(int)
    return df.sort_values(["dt_ref", "driverid"]).reset_index(drop=True)


@st.cache_data(ttl=TTL, show_spinner=False)
def load_driver_meta() -> pd.DataFrame:
    """Nome, sigla e equipe mais recentes de cada piloto (camada bronze).

    E enriquecimento cosmetico: se a tabela nao tiver essas colunas, a UI cai
    para o proprio driverid formatado.
    """
    cfg = get_settings()
    try:
        return _run(
            "SELECT driverid, fullname, abbreviation, teamname FROM ("
            "  SELECT DriverId AS driverid, FullName AS fullname,"
            "         Abbreviation AS abbreviation, TeamName AS teamname,"
            "         ROW_NUMBER() OVER (PARTITION BY DriverId ORDER BY Date DESC) AS rn"
            f"  FROM {cfg.results_table}"
            ") WHERE rn = 1"
        )
    except WarehouseError:
        return pd.DataFrame(columns=["driverid", "fullname", "abbreviation", "teamname"])


@st.cache_data(ttl=TTL, show_spinner=False)
def load_standings(year: int, dt_ref) -> pd.DataFrame:
    """Pontos acumulados no campeonato ate a data de referencia (contexto real)."""
    cfg = get_settings()
    date_str = _safe_date(dt_ref)
    try:
        return _run(
            "SELECT DriverId AS driverid, SUM(Points) AS pontos,"
            "       COUNT(*) AS sessoes"
            f" FROM {cfg.results_table}"
            f" WHERE Year = {int(year)} AND date(Date) <= date('{date_str}')"
            "   AND Mode IN ('Race', 'Sprint')"
            " GROUP BY DriverId"
        )
    except WarehouseError:
        return pd.DataFrame(columns=["driverid", "pontos", "sessoes"])


@st.cache_data(ttl=TTL, show_spinner=False)
def load_events(year: int) -> pd.DataFrame:
    """Sessoes da temporada (corrida e sprint) com rodada, evento e pais.

    Cada data de referencia da ABT corresponde a uma sessao -- por isso da para
    rotular o seletor com o GP em vez de so a data.
    """
    cfg = get_settings()
    try:
        df = _run(
            "SELECT date(Date) AS dt_ref, Mode AS modo, RoundNumber AS rodada,"
            "       EventName AS evento, Country AS pais"
            f" FROM {cfg.results_table}"
            f" WHERE Year = {int(year)} AND Mode IN ('Race', 'Sprint')"
            " GROUP BY 1, 2, 3, 4, 5"
        )
    except WarehouseError:
        return pd.DataFrame(columns=["dt_ref", "modo", "rodada", "evento", "pais"])
    if df.empty:
        return df
    df["dt_ref"] = pd.to_datetime(df["dt_ref"])
    return df.sort_values("dt_ref").reset_index(drop=True)


def event_label(evento: str, rodada, modo: str = "Race", curto: bool = False) -> str:
    """`Hungarian Grand Prix` + rodada 11 -> `R11 · Hungarian GP` (ou so `Hungarian GP`).

    Mantemos o nome como vem do dado. Traduzir por pais seria ambiguo: Miami,
    Austin e Las Vegas sao todos `United States`.
    """
    nome = str(evento).replace("Grand Prix", "GP").strip()
    sufixo = "" if modo == "Race" else f" ({modo})"
    if curto:
        return f"{nome}{sufixo}"
    try:
        return f"R{int(rodada)} · {nome}{sufixo}"
    except (TypeError, ValueError):
        return f"{nome}{sufixo}"


def event_info(year: int) -> dict:
    """{Timestamp da sessao: {"lista": ..., "prosa": ...}} para a temporada.

    Dois formatos porque servem a leituras diferentes: `R11 · Hungarian GP` e
    otimo para varrer uma lista, e pessimo no meio de uma frase.
    """
    eventos = load_events(year)
    if eventos.empty:
        return {}

    mapa = {}
    for linha in eventos.itertuples():
        nome = str(linha.evento).replace("Grand Prix", "GP").strip()
        try:
            rodada = f" (rodada {int(linha.rodada)})"
        except (TypeError, ValueError):
            rodada = ""
        # Sprint entra como prefixo: `Chinese GP (Sprint) (rodada 2)` fica ilegivel.
        prosa = f"sprint do {nome}{rodada}" if linha.modo == "Sprint" else f"{nome}{rodada}"
        mapa[pd.Timestamp(linha.dt_ref)] = {
            "lista": event_label(linha.evento, linha.rodada, linha.modo),
            "prosa": prosa,
        }
    return mapa


def display_names(df: pd.DataFrame) -> pd.DataFrame:
    """Anexa colunas `piloto` e `equipe` a um frame que tenha `driverid`."""
    meta = load_driver_meta()
    out = df.copy()
    fallback = out["driverid"].str.replace("_", " ").str.title()
    if meta.empty:
        out["piloto"] = fallback
        out["equipe"] = "--"
        return out
    out = out.merge(meta, on="driverid", how="left")
    out["piloto"] = out.get("fullname").fillna(fallback) if "fullname" in out else fallback
    out["equipe"] = out.get("teamname").fillna("--") if "teamname" in out else "--"
    return out
