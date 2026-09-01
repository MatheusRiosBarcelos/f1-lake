"""Diagnostico do endpoint de serving: formato de payload aceito e tipo de saida.

Uso:
    python scripts/probe_endpoint.py    # le DATABRICKS_* do .env e usa uma linha real da ABT

    # so se quiser sobrescrever o warehouse do .env:
    python scripts/probe_endpoint.py --http-path /sql/1.0/warehouses/xxxxxxxx
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ENDPOINT = os.getenv(
    "SERVING_ENDPOINT_URL",
    "https://dbc-eb5c1364-5cd5.cloud.databricks.com/serving-endpoints/f1-champions/invocations",
)
TOKEN = os.getenv("DATABRICKS_TOKEN")


def linha_real(http_path: str) -> dict:
    from databricks import sql

    host = ENDPOINT.split("/")[2]
    tabela = os.getenv("ABT_TABLE", "lakehouse.gold.abt_f1_drivers_champion")
    with sql.connect(server_hostname=host, http_path=http_path, access_token=TOKEN) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {tabela} ORDER BY dt_ref DESC LIMIT 1")
            colunas = [c[0].lower() for c in cur.description]
            valores = list(cur.fetchone())
    registro = dict(zip(colunas, valores))
    for chave in ("dt_ref", "driverid", "flchampion", "year"):
        registro.pop(chave, None)
    return {k: (None if v is None else float(v)) for k, v in registro.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--http-path",
        default=os.getenv("DATABRICKS_HTTP_PATH"),
        help="SQL Warehouse para puxar uma linha real da ABT "
             "(padrao: DATABRICKS_HTTP_PATH do .env)",
    )
    args = parser.parse_args()

    if args.http_path and "/sql/1.0/warehouses/" not in args.http_path:
        print(
            f"Caminho suspeito: {args.http_path}\n"
            "O formato correto e /sql/1.0/warehouses/<id> (warehouses no plural).",
            file=sys.stderr,
        )
        return 1

    if not TOKEN:
        print("DATABRICKS_TOKEN nao definido.", file=sys.stderr)
        return 1

    if args.http_path:
        print(f"Warehouse: {args.http_path}")
        registro = linha_real(args.http_path)
        print(f"Linha real da ABT com {len(registro)} features.")
    else:
        print(
            "Sem DATABRICKS_HTTP_PATH no .env e sem --http-path: enviando payload vazio "
            "so para ver a mensagem de erro do schema."
        )
        registro = {}

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    formatos = {
        "dataframe_split": {
            "dataframe_split": {"columns": list(registro), "data": [list(registro.values())]}
        },
        "dataframe_records": {"dataframe_records": [registro]},
        "inputs": {"inputs": {k: [v] for k, v in registro.items()}},
    }

    for nome, payload in formatos.items():
        resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60)
        print(f"\n=== {nome} -> HTTP {resp.status_code}")
        print(resp.text[:600])
        if resp.status_code == 200:
            preds = resp.json().get("predictions")
            print("predictions:", json.dumps(preds)[:200])
            achatado = preds[0] if isinstance(preds, list) and preds else None
            if isinstance(achatado, (int, float)) and float(achatado) in (0.0, 1.0):
                print(
                    "\nATENCAO: a saida parece ser CLASSE (0/1), nao probabilidade.\n"
                    "Registre o modelo com o wrapper de ml_champion/serve_proba.py."
                )
            else:
                print("\nOK: a saida parece ser probabilidade continua.")
            return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
