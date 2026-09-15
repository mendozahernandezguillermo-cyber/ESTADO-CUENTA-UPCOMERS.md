#!/usr/bin/env python3
"""
Descarga OHLC diario de los indices via Yahoo, para la prueba de replicacion
cruzada de la descomposicion intradia/nocturno.

Por que esto y no Dukascopy M15:
  - La descomposicion solo necesita apertura y cierre de sesion: 2 numeros al
    dia. Bajar 26.000 velas M15 por ano era desproporcionado.
  - dukascopy-node construye las velas desde ficheros HORARIOS: un ano son
    ~6.000 peticiones, y por eso saltaba el 429.
  - Y la apertura/cierre de Yahoo son las OFICIALES del indice de contado,
    que es mas correcto para esto que un feed de CFD.

VERIFICACION CRITICA incluida: en algunos indices Yahoo devuelve Open igual al
cierre anterior (dato rellenado, no real). Si eso pasa, el retorno nocturno
sale cero por construccion y la descomposicion es basura. Se mide antes de
usar los datos.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf

DIR = "yahoo"
os.makedirs(DIR, exist_ok=True)

TICKERS = {
    "^NDX":   ("NASDAQ 100",    "EEUU"),
    "^GSPC":  ("S&P 500",       "EEUU"),
    "^DJI":   ("Dow 30",        "EEUU"),
    "^RUT":   ("Russell 2000",  "EEUU"),
    "^GDAXI": ("DAX",           "EUROPA"),
    "^FTSE":  ("FTSE 100",      "EUROPA"),
    "^N225":  ("Nikkei 225",    "ASIA"),
    "^AXJO":  ("ASX 200",       "ASIA"),
    "GC=F":   ("Oro futuro",    "CONTROL"),
}

INICIO = "2000-01-01"

print("=" * 82)
print("DESCARGA Y CONTROL DE CALIDAD")
print("=" * 82)
print(f"{'indice':<16}{'bloque':<9}{'sesiones':>9}{'desde':>12}"
      f"{'Open==PrevClose':>17}{'Open==Close':>13}")
print("-" * 82)

datos = {}
for tk, (nom, blq) in TICKERS.items():
    p = os.path.join(DIR, "%s.csv" % tk.replace("^", "").replace("=", ""))
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        df = pd.read_csv(p, index_col=0, parse_dates=True)
    else:
        df = yf.download(tk, start=INICIO, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df is None or len(df) == 0:
            print(f"{nom:<16}{blq:<9}{'[sin datos]':>9}")
            continue
        df.to_csv(p)

    df = df[["Open", "High", "Low", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    prev = df["Close"].shift(1)

    # --- control de calidad ---
    # Open identico al cierre anterior => dato rellenado, no real
    igual_prev = (np.abs(df["Open"] / prev - 1.0) < 1e-9).mean()
    # Open identico al Close del mismo dia => barra degenerada
    igual_close = (np.abs(df["Open"] / df["Close"] - 1.0) < 1e-9).mean()

    datos[tk] = (df, nom, blq, igual_prev)
    aviso = "  <-- SOSPECHOSO" if igual_prev > 0.10 else ""
    print(f"{nom:<16}{blq:<9}{len(df):>9}{str(df.index.min().date()):>12}"
          f"{igual_prev:>16.1%}{igual_close:>13.1%}{aviso}")

print()
print("Lectura del control: si 'Open==PrevClose' es alto, Yahoo no da la")
print("apertura real de ese indice y el tramo nocturno seria cero artificial.")
print("Esos indices hay que descartarlos de la prueba, no arreglarlos.")

# guardar el resumen para el analisis
with open(os.path.join(DIR, "_calidad.csv"), "w") as f:
    f.write("ticker,nombre,bloque,frac_open_igual_prevclose,sesiones\n")
    for tk, (df, nom, blq, ip) in datos.items():
        f.write("%s,%s,%s,%.6f,%d\n" % (tk, nom, blq, ip, len(df)))
print("\nGuardado %s/_calidad.csv" % DIR)
