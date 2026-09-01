"""Configuracao da aplicacao: lida de st.secrets (Streamlit Cloud) ou do ambiente."""

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import streamlit as st

try:  # opcional: local usamos .env, no Streamlit Cloud usamos st.secrets
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

DEFAULT_ENDPOINT = (
    "https://dbc-eb5c1364-5cd5.cloud.databricks.com"
    "/serving-endpoints/f1-champions/invocations"
)
DEFAULT_ABT_TABLE = "lakehouse.gold.abt_f1_drivers_champion"
DEFAULT_RESULTS_TABLE = "lakehouse.bronze.f1_results"


def _get(key: str, default: str | None = None) -> str | None:
    """Ordem: st.secrets (Streamlit Cloud) -> variavel de ambiente / .env -> default."""
    try:
        if key in st.secrets:
            value = st.secrets[key]
            if value not in (None, ""):
                return str(value)
    except Exception:
        # secrets.toml inexistente (rodando local sem arquivo)
        pass
    value = os.getenv(key, default)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    endpoint_url: str
    token: str | None
    http_path: str | None
    server_hostname: str
    abt_table: str
    results_table: str

    @property
    def has_warehouse(self) -> bool:
        return bool(self.token and self.http_path)

    @property
    def has_endpoint(self) -> bool:
        return bool(self.token and self.endpoint_url)

    @property
    def missing(self) -> list[str]:
        faltando = []
        if not self.token:
            faltando.append("DATABRICKS_TOKEN")
        if not self.http_path:
            faltando.append("DATABRICKS_HTTP_PATH")
        return faltando


@st.cache_resource
def get_settings() -> Settings:
    endpoint = _get("SERVING_ENDPOINT_URL", DEFAULT_ENDPOINT)
    host = _get("DATABRICKS_HOST") or urlparse(endpoint).netloc
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    return Settings(
        endpoint_url=endpoint,
        token=_get("DATABRICKS_TOKEN"),
        http_path=_get("DATABRICKS_HTTP_PATH"),
        server_hostname=host,
        abt_table=_get("ABT_TABLE", DEFAULT_ABT_TABLE),
        results_table=_get("RESULTS_TABLE", DEFAULT_RESULTS_TABLE),
    )
