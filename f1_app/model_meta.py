"""Metadados do modelo lidos dos artefatos versionados no repositorio."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
IMPORTANCES = ROOT / "ml_champion" / "feature_importances.md"
ROC_CURVE = ROOT / "ml_champion" / "roc_curve.png"

# Metricas registradas no MLflow tracking (Databricks).
METRICS = {"Treino": 0.995, "Teste": 0.9999, "Out-of-time (2025)": 0.955}

# Rotulos legiveis para as features mais relevantes.
LABELS = {
    "avg_gridposition": "Posicao media de largada",
    "avg_position": "Posicao media de chegada",
    "avg_overtake": "Media de ultrapassagens",
    "qtde_1pos": "Vitorias",
    "qtde_podios": "Podios",
    "qtde_pos5": "Top 5",
    "qtde_gridpos5": "Largadas no top 5",
    "qtde_1_gridposition": "Poles",
    "qtde_pole_win": "Poles convertidas em vitoria",
    "qtde_points": "Pontos",
    "qtde_sessions_with_points": "Sessoes pontuando",
    "qtde_sessions_with_overtake": "Sessoes com ultrapassagem",
    "qtde_sessions_finesshed": "Sessoes concluidas",
    "qtde_sessions": "Sessoes",
    "qtde_seasons": "Temporadas",
    "qtde_race": "Corridas",
    "qtde_sprint": "Sprints",
}
JANELAS = {
    "last10": "ult. 10",
    "last20": "ult. 20",
    "last40": "ult. 40",
    "life": "carreira",
}


def humanize(feature: str) -> str:
    """`avg_gridposition_race_last20` -> `Posicao media de largada · corrida · ult. 20`."""
    resto = feature
    janela = ""
    for sufixo, rotulo in JANELAS.items():
        if resto.endswith("_" + sufixo):
            resto, janela = resto[: -len(sufixo) - 1], rotulo
            break

    modo = ""
    for sufixo, rotulo in (("_race", "corrida"), ("_sprint", "sprint")):
        if resto.endswith(sufixo):
            resto, modo = resto[: -len(sufixo)], rotulo
            break

    base = LABELS.get(resto, resto.replace("_", " ").capitalize())
    partes = [base] + [p for p in (modo, janela) if p]
    return " · ".join(partes)


@st.cache_data(show_spinner=False)
def feature_importances() -> pd.DataFrame:
    """Le a tabela markdown exportada do MLflow."""
    if not IMPORTANCES.exists():
        return pd.DataFrame(columns=["feature", "importancia", "rotulo"])

    linhas = []
    for linha in IMPORTANCES.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|") or set(linha) <= set("|-: "):
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if len(celulas) != 2 or not celulas[0]:
            continue
        try:
            valor = float(celulas[1])
        except ValueError:
            continue  # cabecalho
        linhas.append((celulas[0], valor))

    df = pd.DataFrame(linhas, columns=["feature", "importancia"])
    df["rotulo"] = df["feature"].map(humanize)
    return df.sort_values("importancia", ascending=False).reset_index(drop=True)


def top_features(n: int, disponiveis: list[str] | None = None) -> list[str]:
    """As n features mais importantes, opcionalmente filtradas pelas colunas da ABT."""
    df = feature_importances()
    nomes = df.loc[df["importancia"] > 0, "feature"].tolist()
    if disponiveis is not None:
        existentes = {c.lower() for c in disponiveis}
        nomes = [f for f in nomes if f.lower() in existentes]
    return nomes[:n]
