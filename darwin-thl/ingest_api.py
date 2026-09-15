"""
Descarga cotizacion historica y historico de atributos (badges) de un DARWIN
usando las 3 APIs de datos de Darwinex (token de ~6 meses).

Uso:
    cp .env.example .env      # y rellena DARWINEX_ACCESS_TOKEN + DARWIN_PRODUCT
    pip install -r requirements.txt
    python3 ingest_api.py

Guarda en data/:
    {TICKER}_quotes_raw.json      respuesta cruda (por si el parseo falla)
    {TICKER}_quotes.csv           serie de cotizacion
    {TICKER}_badges_raw.json      respuesta cruda
    {TICKER}_badges.csv           historico de los 12 atributos + D-Score

Limites de la API (respetados con pausas):
    DARWIN Info API   10 req/min
    DARWIN Quotes API  1 req/min
    Por usuario       50 req/min
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from darwinexapis.API.InfoAPI.DWX_Info_API import DWX_Info_API

# Orden documentado del array de atributos en la serie BADGES
BADGE_COLUMNS = [
    "EX",  # Experience
    "MC",  # Market Correlation
    "RS",  # Risk Stability
    "RA",  # Risk Adjustment
    "OS",  # Open Strategy
    "CS",  # Close Strategy
    "R+",  # Winning Consistency
    "R-",  # Losing Consistency
    "DC",  # Duration Consistency
    "LA",  # Loss Aversion
    "PF",  # Performance
    "CP",  # Scalability / Capacity
    "D-Score",
]

DATA_DIR = Path(__file__).parent / "data"


def build_api() -> DWX_Info_API:
    token = os.getenv("DARWINEX_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit(
            "ERROR: falta DARWINEX_ACCESS_TOKEN en .env\n"
            "Generalo en https://www.darwinex.com/data/darwin-api "
            "eligiendo la opcion de SOLO las 3 APIs de datos."
        )

    auth = {
        "access_token": token,
        "consumer_key": os.getenv("DARWINEX_CONSUMER_KEY", ""),
        "consumer_secret": os.getenv("DARWINEX_CONSUMER_SECRET", ""),
        "refresh_token": os.getenv("DARWINEX_REFRESH_TOKEN", ""),
    }
    # _demo=False -> entorno PRODUCTION (ambos entornos sirven datos reales de DARWINs)
    return DWX_Info_API(auth, _version=1.5, _demo=False)


def dump_raw(name: str, payload) -> None:
    path = DATA_DIR / f"{name}_raw.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(f"  raw -> {path}")


def to_frame(payload):
    """La libreria puede devolver DataFrame, dict o lista. Normalizamos."""
    if isinstance(payload, pd.DataFrame):
        return payload
    try:
        return pd.json_normalize(payload)
    except Exception:
        return None


def fetch_quotes(api: DWX_Info_API, product: str, ticker: str) -> None:
    print(f"\n[1/2] Cotizacion historica de {product} ...")
    payload = api._Get_Historical_Quotes_(_symbols=[product], _plot=False)
    dump_raw(f"{ticker}_quotes", payload)

    df = to_frame(payload)
    if df is None or df.empty:
        print("  AVISO: no se pudo normalizar. Revisa el JSON crudo.")
        return

    out = DATA_DIR / f"{ticker}_quotes.csv"
    df.to_csv(out, index=True)
    print(f"  {len(df)} filas -> {out}")
    print(df.head(3).to_string())


def fetch_badges(api: DWX_Info_API, product: str, ticker: str) -> None:
    print(f"\n[2/2] Historico de atributos (badges) de {product} ...")
    payload = api._Get_Historical_Scores_(_symbols=[product], _plot=False)
    dump_raw(f"{ticker}_badges", payload)

    df = to_frame(payload)
    if df is None or df.empty:
        print("  AVISO: no se pudo normalizar. Revisa el JSON crudo.")
        return

    # Si viene una columna con el array de 13 scores, la expandimos
    for col in df.columns:
        sample = df[col].dropna().head(1)
        if len(sample) and isinstance(sample.iloc[0], (list, tuple)):
            if len(sample.iloc[0]) == len(BADGE_COLUMNS):
                expanded = pd.DataFrame(
                    df[col].tolist(), columns=BADGE_COLUMNS, index=df.index
                )
                df = pd.concat([df.drop(columns=[col]), expanded], axis=1)
                print(f"  columna '{col}' expandida en {len(BADGE_COLUMNS)} atributos")
                break

    out = DATA_DIR / f"{ticker}_badges.csv"
    df.to_csv(out, index=True)
    print(f"  {len(df)} filas -> {out}")
    print(df.head(3).to_string())


def main() -> None:
    load_dotenv()
    DATA_DIR.mkdir(exist_ok=True)

    ticker = os.getenv("DARWIN_TICKER", "THL").strip()
    product = os.getenv("DARWIN_PRODUCT", "").strip()

    if not product or product.endswith("XX"):
        sys.exit(
            "ERROR: falta DARWIN_PRODUCT en .env (nombre largo, p.ej. THL.4.12).\n"
            "Sacalo de la URL del perfil del DARWIN: darwinex.com/darwin/THL.4.XX"
        )

    api = build_api()
    fetch_quotes(api, product, ticker)
    time.sleep(7)  # Info API: 10 req/min
    fetch_badges(api, product, ticker)

    print("\nListo. Siguiente paso: auditoria estadistica sobre data/*.csv")


if __name__ == "__main__":
    main()
