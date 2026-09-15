#!/usr/bin/env python3
"""
Extrae las ENTRADAS de NASDAQ de THL a partir de la linea temporal de
estados del journal.

El journal no lista operaciones: lista momentos en que la composicion de
la cartera cambia. El campo c9 enumera los instrumentos abiertos con su
signo ('+' largo, '-' corto, '' plano). Una entrada de NASDAQ es una
transicion en la que el NASDAQ pasa de ausente a presente.
"""
import json
import re
import numpy as np
import pandas as pd

with open("j1.json") as f:
    raw = json.load(f)

df = pd.DataFrame(raw, columns=["c%d" % i for i in range(11)])
df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
df = df.sort_values("ts").reset_index(drop=True)

print("=== ESTADISTICOS DE CAMPOS (para acabar de identificarlos) ===")
for c in ["c0", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c10"]:
    s = pd.to_numeric(df[c], errors="coerce")
    print("  %-4s min=%12.2f max=%14.2f media=%11.2f distintos=%5d"
          % (c, s.min(), s.max(), s.mean(), s.nunique()))
print()


def nasdaq_state(txt):
    """Devuelve +1, -1, 0 (ambos/hedge) o None si el NASDAQ no esta abierto."""
    if not isinstance(txt, str) or "NASDAQ" not in txt:
        return None
    for parte in txt.split(","):
        parte = parte.strip()
        if "NASDAQ" in parte:
            if parte.startswith("+"):
                return 1
            if parte.startswith("-"):
                return -1
            return 0
    return None


df["nas"] = df["c9"].apply(nasdaq_state)

#--- transiciones ausente -> presente = ENTRADA ---------------------
prev = df["nas"].shift(1)
entrada = df["nas"].notna() & prev.isna()
salida = df["nas"].isna() & prev.notna()

ent = df[entrada].copy()
print("Registros totales ............ %d" % len(df))
print("ENTRADAS de NASDAQ ........... %d" % len(ent))
print("SALIDAS de NASDAQ ............ %d" % int(salida.sum()))
print()

#--- duracion: emparejar cada entrada con la siguiente salida -------
idx_ent = np.where(entrada.to_numpy())[0]
idx_sal = np.where(salida.to_numpy())[0]
dur = []
for i in idx_ent:
    j = idx_sal[idx_sal > i]
    if len(j):
        dur.append((df["ts"].iloc[int(j[0])] - df["ts"].iloc[i]).total_seconds() / 60.0)
    else:
        dur.append(np.nan)
ent["dur_min"] = dur

d = pd.Series(dur).dropna()
print("=== DURACION de las posiciones de NASDAQ (minutos) ===")
print("  n=%d  media=%.1f  mediana=%.1f  p25=%.1f  p75=%.1f"
      % (len(d), d.mean(), d.median(), d.quantile(.25), d.quantile(.75)))
print("  THL publica: duracion media 169 min (2h49m)")
print()

#--- horario de las entradas, en hora de NUEVA YORK -----------------
ent["ny"] = ent["ts"].dt.tz_convert("America/New_York")
ent["cet"] = ent["ts"].dt.tz_convert("Europe/Madrid")
ent["ny_min"] = ent["ny"].dt.hour * 60 + ent["ny"].dt.minute
ent["desde_apertura"] = ent["ny_min"] - (9 * 60 + 30)
ent["dow"] = ent["ny"].dt.dayofweek

print("=== ENTRADAS por hora de NUEVA YORK ===")
h = ent["ny"].dt.hour
mx = h.value_counts().max()
for hh in range(24):
    n = int((h == hh).sum())
    if n:
        print("  %02dh NY  %4d  %5.2f%%  %s"
              % (hh, n, 100.0 * n / len(ent), "#" * int(50.0 * n / mx)))
print()

print("=== ENTRADAS relativas a la apertura cash (09:30 NY) ===")
bins = [-10000, -180, -60, -1, 0, 15, 30, 60, 120, 180, 240, 390, 10000]
lab = ["antes -3h", "-3h a -1h", "-1h a 0", "apertura exacta",
       "0 a +15m", "+15 a +30m", "+30m a +1h", "+1h a +2h",
       "+2h a +3h", "+3h a +4h", "+4h a cierre", "tras cierre"]
cut = pd.cut(ent["desde_apertura"], bins=bins, labels=lab, right=False)
for k, v in cut.value_counts().reindex(lab).items():
    if v and not np.isnan(v):
        print("  %-18s %4d  %5.2f%%" % (k, int(v), 100.0 * v / len(ent)))
print()

print("=== DIRECCION de las entradas ===")
for k, v in ent["nas"].value_counts().items():
    nom = {1.0: "LARGO", -1.0: "CORTO", 0.0: "hedge"}.get(k, str(k))
    print("  %-8s %4d  (%.2f%%)" % (nom, v, 100.0 * v / len(ent)))
print()

print("=== DIA DE LA SEMANA ===")
for k, v in ent["dow"].value_counts().sort_index().items():
    print("  %-4s %4d  (%.2f%%)"
          % (["lun", "mar", "mie", "jue", "vie", "sab", "dom"][int(k)],
             v, 100.0 * v / len(ent)))
print()

print("=== RANGO ===")
print("  %s  ->  %s" % (ent["ny"].min(), ent["ny"].max()))
print("  entradas por mes: %.1f" % (len(ent) /
      ((ent["ts"].max() - ent["ts"].min()).days / 30.44)))
print("  THL publica: 47 operaciones/mes en total (4 activos)")

out = ent[["ts", "ny", "cet", "ny_min", "desde_apertura", "dow",
           "nas", "dur_min", "c9"]].copy()
out.to_csv("entradas_nasdaq.csv", index=False)
print()
print("Guardado entradas_nasdaq.csv (%d filas)" % len(out))
