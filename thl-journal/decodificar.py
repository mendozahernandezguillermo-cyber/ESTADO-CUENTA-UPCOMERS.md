#!/usr/bin/env python3
"""
Decodifica el journal de THL descargado del endpoint publico
/api/tradingaccounts/tradingjournal

Cada registro es un array de 11 campos. Hay que deducir que es cada uno
contrastando contra los datos conocidos de la pagina de THL:
  2.400 operaciones, 65.83% acierto, duracion media 2h49m (169 min),
  85% NASDAQ 100 (Mini), 4 activos, sesion americana 51.79%.
"""
import json
import numpy as np
import pandas as pd

with open("j1.json") as f:
    raw = json.load(f)

print("Registros: %d" % len(raw))
print("Campos por registro: %s" % sorted(set(len(r) for r in raw)))
print()

df = pd.DataFrame(raw, columns=["c%d" % i for i in range(11)])
df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
df["cet"] = df["ts"].dt.tz_convert("Europe/Madrid")
df["ny"] = df["ts"].dt.tz_convert("America/New_York")

print("Rango temporal: %s  ->  %s"
      % (df["cet"].iloc[0], df["cet"].iloc[-1]))
print()

print("=== ESTADISTICOS DE CADA CAMPO ===")
for c in ["c0", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c10"]:
    s = pd.to_numeric(df[c], errors="coerce")
    print("  %-4s min=%12.3f  max=%14.3f  media=%11.3f  "
          "distintos=%d" % (c, s.min(), s.max(), s.mean(), s.nunique()))
print()

print("=== CAMPO c9 (instrumento + direccion) ===")
vc = df["c9"].value_counts()
print("  valores distintos: %d" % len(vc))
for k, v in vc.items():
    print("    %-30s %5d  (%.2f%%)" % (repr(k), v, 100.0 * v / len(df)))
print()

#--- separar signo e instrumento ------------------------------------
sig = df["c9"].astype(str)
df["dir"] = np.where(sig.str.startswith("+"), 1,
                     np.where(sig.str.startswith("-"), -1, 0))
df["inst"] = sig.str.lstrip("+-")

print("=== INSTRUMENTOS (sin signo) ===")
for k, v in df["inst"].value_counts().items():
    print("  %-30s %5d  (%.2f%%)" % (k, v, 100.0 * v / len(df)))
print()
print("=== DIRECCION ===")
for k, v in df["dir"].value_counts().items():
    nom = {1: "LARGO", -1: "CORTO", 0: "(vacio)"}[k]
    print("  %-10s %5d  (%.2f%%)" % (nom, v, 100.0 * v / len(df)))
print()

#--- que campo es la duracion? --------------------------------------
print("=== BUSCANDO LA DURACION (THL: media 169 min) ===")
for c in ["c0", "c4", "c7", "c8", "c10"]:
    s = pd.to_numeric(df[c], errors="coerce")
    print("  %-4s  media=%9.2f   si son minutos -> %6.2f h   "
          "si son segundos -> %6.2f min"
          % (c, s.mean(), s.mean() / 60.0, s.mean() / 60.0))
print()

#--- reparto horario, contra el 51.79% de sesion americana ----------
print("=== REPARTO HORARIO (CET) de las entradas ===")
h = df[df["inst"] != ""]["cet"].dt.hour
tot = len(h)
for hh in range(24):
    n = int((h == hh).sum())
    if n:
        bar = "#" * int(60.0 * n / max(1, h.value_counts().max()))
        print("  %02dh  %5d  %5.2f%%  %s" % (hh, n, 100.0 * n / tot, bar))
print()
print("Pico esperado segun la pagina de THL: 15h CET, cola 16-17h")
print()

#--- separacion entre registros consecutivos -----------------------
d = df["c1"].diff().dropna() / 1000.0
print("=== SEPARACION entre registros consecutivos (segundos) ===")
print("  mediana=%.1f  p25=%.1f  p75=%.1f  min=%.1f  max=%.1f"
      % (d.median(), d.quantile(.25), d.quantile(.75), d.min(), d.max()))

df.to_csv("journal_decodificado.csv", index=False)
print()
print("Guardado journal_decodificado.csv (%d filas)" % len(df))
