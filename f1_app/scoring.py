"""Cliente do endpoint de model serving do Databricks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests
import streamlit as st

from f1_app.config import get_settings

# Colunas da ABT que nao sao features (o treino usa `df.columns[4:]` apos o
# merge por driverid/year/flChampion/dt_ref).
NON_FEATURES = {"dt_ref", "driverid", "flchampion", "year"}

BATCH_SIZE = 200
TIMEOUT = 90


class ScoringError(RuntimeError):
    """Falha na chamada ao endpoint."""


@dataclass
class ScoreResult:
    values: np.ndarray
    is_probability: bool

    @property
    def as_series(self) -> pd.Series:
        return pd.Series(self.values)


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.lower() not in NON_FEATURES]


def _payloads(frame: pd.DataFrame) -> list[dict]:
    """Formatos aceitos pelo MLflow serving, em ordem de preferencia."""
    clean = frame.astype(object).where(pd.notnull(frame), None)
    columns = list(clean.columns)
    data = clean.values.tolist()
    return [
        {"dataframe_split": {"columns": columns, "data": data}},
        {"dataframe_records": clean.to_dict(orient="records")},
        {"inputs": clean.to_dict(orient="list")},
    ]


def _parse(predictions) -> np.ndarray:
    """Normaliza os formatos possiveis de `predictions` para um vetor 1-D."""
    if isinstance(predictions, dict):
        predictions = predictions.get("predictions", predictions)

    out = []
    for item in predictions:
        if isinstance(item, dict):
            # {"0": p0, "1": p1} ou {"prediction": x}
            if "1" in item:
                out.append(float(item["1"]))
            elif 1 in item:
                out.append(float(item[1]))
            else:
                out.append(float(next(iter(item.values()))))
        elif isinstance(item, (list, tuple)):
            # predict_proba devolve [p_classe0, p_classe1]
            out.append(float(item[-1]))
        else:
            out.append(float(item))
    return np.asarray(out, dtype=float)


def _post(payload: dict) -> requests.Response:
    cfg = get_settings()
    return requests.post(
        cfg.endpoint_url,
        headers={
            "Authorization": f"Bearer {cfg.token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=TIMEOUT,
    )


def _score_batch(frame: pd.DataFrame) -> np.ndarray:
    erros = []
    for payload in _payloads(frame):
        try:
            resp = _post(payload)
        except requests.RequestException as err:
            raise ScoringError(f"Falha de rede ao chamar o endpoint: {err}") from err

        if resp.status_code == 200:
            body = resp.json()
            return _parse(body.get("predictions", body))

        if resp.status_code in (401, 403):
            raise ScoringError(
                "Token recusado pelo endpoint (401/403). Verifique DATABRICKS_TOKEN "
                "e se ele tem permissao CAN QUERY no serving endpoint."
            )
        if resp.status_code == 404:
            raise ScoringError(
                "Endpoint nao encontrado (404). Confira SERVING_ENDPOINT_URL."
            )
        erros.append(f"HTTP {resp.status_code}: {resp.text[:300]}")

    raise ScoringError(
        "Nenhum formato de payload foi aceito pelo endpoint.\n" + "\n".join(erros)
    )


@st.cache_data(ttl=15 * 60, show_spinner="Consultando o modelo...")
def score(df: pd.DataFrame) -> ScoreResult:
    """Pontua um frame da ABT e devolve a probabilidade de titulo por linha."""
    if df.empty:
        return ScoreResult(np.array([]), True)

    cfg = get_settings()
    if not cfg.has_endpoint:
        raise ScoringError("DATABRICKS_TOKEN ausente -- nao da para chamar o endpoint.")

    frame = df[feature_columns(df)].apply(pd.to_numeric, errors="coerce")

    partes = [
        _score_batch(frame.iloc[i : i + BATCH_SIZE])
        for i in range(0, len(frame), BATCH_SIZE)
    ]
    values = np.concatenate(partes) if partes else np.array([])

    # Se o modelo foi logado com o flavor sklearn padrao, `predict` devolve a
    # classe (0/1) e nao a probabilidade -- o ranking fica inutil. Detectamos.
    finitos = values[np.isfinite(values)]
    is_prob = finitos.size == 0 or not np.all(np.isin(finitos, (0.0, 1.0)))
    return ScoreResult(values, bool(is_prob))


def attach_scores(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Devolve o frame com a coluna `proba` e a flag de probabilidade real."""
    result = score(df)
    out = df.copy()
    out["proba"] = result.values
    return out, result.is_probability
