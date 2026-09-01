"""Diagnostico de credenciais: diz que tipo de token voce tem e o que ele alcanca.

    python scripts/check_auth.py

Nao imprime o token. De um JWT, mostra apenas os escopos e a validade.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import sys

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TOKEN = os.getenv("DATABRICKS_TOKEN", "")
HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "")
ENDPOINT = os.getenv(
    "SERVING_ENDPOINT_URL",
    "https://dbc-eb5c1364-5cd5.cloud.databricks.com/serving-endpoints/f1-champions/invocations",
)
HOST = os.getenv("DATABRICKS_HOST") or ENDPOINT.split("/")[2]
BASE = f"https://{HOST.replace('https://', '').rstrip('/')}"
HEAD = {"Authorization": f"Bearer {TOKEN}"}

OK, FAIL, WARN = "  [ok]  ", " [FALHA]", " [aviso]"


def tipo_do_token() -> str:
    if not TOKEN:
        print(f"{FAIL} DATABRICKS_TOKEN vazio. Preencha o .env.")
        sys.exit(1)

    if TOKEN.startswith("dapi"):
        print(f"{OK} Tipo: Personal Access Token (dapi...).")
        print("         Atencao: um PAT PODE ser emitido com escopos restritos.")
        print("         O mapa de escopos abaixo mostra o que este alcanca de fato.")
        return "pat"

    partes = TOKEN.split(".")
    if len(partes) == 3:
        try:
            corpo = partes[1] + "=" * (-len(partes[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(corpo))
        except Exception:
            print(f"{WARN} Tipo: parece JWT, mas nao consegui decodificar.")
            return "jwt"

        escopos = claims.get("scope", "") or " ".join(claims.get("scopes", []))
        exp = claims.get("exp")
        print(f"{WARN} Tipo: token OAuth (JWT), nao um PAT.")
        print(f"         escopos: {escopos or '(nenhum declarado)'}")
        if exp:
            quando = dt.datetime.fromtimestamp(int(exp), dt.timezone.utc)
            restante = quando - dt.datetime.now(dt.timezone.utc)
            estado = "EXPIRADO" if restante.total_seconds() < 0 else f"expira em {restante}"
            print(f"         validade: {quando:%Y-%m-%d %H:%M UTC} ({estado})")
        if "sql" not in escopos and "all-apis" not in escopos:
            print(f"{FAIL} Falta o escopo `sql` -- e exatamente o erro do SQL Warehouse.")
        return "jwt"

    print(f"{WARN} Tipo: formato nao reconhecido (nem `dapi...`, nem JWT).")
    return "?"


def checa(nome: str, url: str, **kwargs) -> dict | None:
    try:
        resp = requests.get(url, headers=HEAD, timeout=30, **kwargs)
    except requests.RequestException as err:
        print(f"{FAIL} {nome}: {err}")
        return None
    if resp.status_code == 200:
        print(f"{OK} {nome}")
        return resp.json()
    print(f"{FAIL} {nome}: HTTP {resp.status_code} -- {resp.text[:200]}")
    return None


SONDAS = [
    ("serving-endpoints", "/api/2.0/serving-endpoints"),
    ("sql", "/api/2.0/sql/warehouses"),
    ("unity-catalog", "/api/2.1/unity-catalog/catalogs"),
    ("workspace", "/api/2.0/workspace/list?path=/"),
    ("mlflow", "/api/2.0/mlflow/experiments/search?max_results=1"),
    ("files", "/api/2.0/fs/directories/Volumes/"),
    ("jobs", "/api/2.2/jobs/list?limit=1"),
    ("clusters", "/api/2.0/clusters/list"),
]


def mapa_de_escopos() -> set[str]:
    """Sonda uma API por escopo e reporta quais o token alcanca."""
    liberados = set()
    for nome, path in SONDAS:
        try:
            resp = requests.get(f"{BASE}{path}", headers=HEAD, timeout=25)
        except requests.RequestException as err:
            print(f"{FAIL} {nome:20} erro de rede: {err}")
            continue
        if resp.status_code == 200:
            print(f"{OK} {nome:20} liberado")
            liberados.add(nome)
        elif resp.status_code == 403 and "scopes" in resp.text:
            print(f"{FAIL} {nome:20} negado (escopo ausente)")
        else:
            print(f"{WARN} {nome:20} HTTP {resp.status_code}")
    return liberados


def main() -> int:
    print(f"\nWorkspace: {BASE}\n")
    tipo = tipo_do_token()

    print("\n--- Identidade ---")
    eu = checa("SCIM /Me (o token autentica?)", f"{BASE}/api/2.0/preview/scim/v2/Me")
    if eu:
        print(f"         usuario: {eu.get('userName', '?')}")

    print("\n--- Escopos efetivos (o que o token realmente alcanca) ---")
    escopos_ok = mapa_de_escopos()

    print("\n--- SQL Warehouse (leitura da ABT) ---")
    lista = checa("Listar warehouses (exige escopo `sql`)", f"{BASE}/api/2.0/sql/warehouses")
    if lista:
        for w in lista.get("warehouses", []):
            caminho = f"/sql/1.0/warehouses/{w['id']}"
            marca = "  <-- e o do seu .env" if caminho == HTTP_PATH else ""
            print(f"         {w.get('state','?'):>8}  {caminho}  {w.get('name','')}{marca}")
        if HTTP_PATH and not any(
            f"/sql/1.0/warehouses/{w['id']}" == HTTP_PATH for w in lista.get("warehouses", [])
        ):
            print(f"{FAIL} DATABRICKS_HTTP_PATH ({HTTP_PATH}) nao bate com nenhum warehouse acima.")

    print("\n--- Serving endpoint (o modelo) ---")
    nome = ENDPOINT.split("/serving-endpoints/")[-1].split("/")[0]
    checa(f"Endpoint `{nome}`", f"{BASE}/api/2.0/serving-endpoints/{nome}")

    print()
    if "sql" in escopos_ok:
        print("=> O token alcanca o SQL Warehouse. O app deve conectar normalmente.")
    elif "serving-endpoints" in escopos_ok:
        print(
            "=> Token restrito: alcanca o serving endpoint, mas NAO o SQL Warehouse.\n"
            "   1) Gere um token em Settings > Developer > Access tokens (token geral,\n"
            "      nao o gerado a partir da tela do serving endpoint) e teste de novo.\n"
            "   2) Se o novo token vier igualmente restrito, a workspace so emite tokens\n"
            "      com escopo limitado -- nesse caso o app precisa ler a ABT de um\n"
            "      snapshot exportado, em vez de consultar o warehouse ao vivo.\n"
        )
    else:
        print("=> O token nao alcanca nem o serving endpoint. Gere um novo PAT.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
