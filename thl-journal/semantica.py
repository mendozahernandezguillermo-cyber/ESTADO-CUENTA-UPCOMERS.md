#!/usr/bin/env python3
"""
Fija la semantica de los 11 campos antes de construir el detector de grid.

Hipotesis a contrastar, mirando las filas de una MISMA posicion:
  c2 = retorno acumulado CERRADO (solo cambia al cerrar)
  c3 = P&L ABIERTO en curso
  c4 = ? decrece mientras c3 mejora
  c5 = constante dentro de una posicion -> tamano / apalancamiento
  c6 = ?  crece de 1 en 1
  c7 = ?  crece
  c8 = ?  DECRECE 3,2,1  -> candidato a "operaciones abiertas"
  c9 = instrumento con signo
"""
import json
import numpy as np
import pandas as pd

df = pd.read_csv("journal_decodificado.csv")
# se reconstruye desde el epoch en ms: mas robusto que parsear el string
df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
df["plano"] = df["inst"].isna() | (df["inst"].astype(str) == "")

print("Registros: %d   planos: %d (%.1f%%)"
      % (len(df), df["plano"].sum(), 100.0 * df["plano"].mean()))
print()

print("=== ¿QUE CAMPOS SE ANULAN AL ESTAR PLANO? ===")
for c in ["c0", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c10"]:
    s = pd.to_numeric(df[c], errors="coerce")
    cero_plano = (s[df["plano"]].abs() < 1e-9).mean()
    cero_abier = (s[~df["plano"]].abs() < 1e-9).mean()
    print("  %-4s  cero cuando plano: %6.1f%%   cero cuando abierto: %6.1f%%"
          % (c, 100 * cero_plano, 100 * cero_abier))
print()

print("=== ESTADISTICOS (solo filas con posicion abierta) ===")
ab = df[~df["plano"]]
for c in ["c0", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c10"]:
    s = pd.to_numeric(ab[c], errors="coerce")
    print("  %-4s min=%12.3f max=%14.3f media=%11.3f distintos=%6d  "
          "enteros=%s" % (c, s.min(), s.max(), s.mean(), s.nunique(),
                          "SI" if np.allclose(s.dropna(),
                                              s.dropna().round()) else "no"))
print()

# ---- segmentar en EPISODIOS: tramos contiguos con posicion abierta ----
df["ep"] = (df["plano"] != df["plano"].shift()).cumsum()
eps = df[~df["plano"]].groupby("ep")

print("=== EPISODIOS (tramos contiguos con posicion abierta) ===")
print("  numero de episodios: %d" % eps.ngroups)
tam = eps.size()
print("  registros por episodio: mediana %.0f  p90 %.0f  max %d"
      % (tam.median(), tam.quantile(.9), tam.max()))
print()

print("=== ¿QUE CAMPOS SON CONSTANTES DENTRO DE UN EPISODIO? ===")
for c in ["c5", "c6", "c7", "c8", "c10"]:
    nun = eps[c].nunique()
    print("  %-4s  constante en %.1f%% de los episodios (mediana de valores"
          " distintos: %.0f)" % (c, 100.0 * (nun == 1).mean(), nun.median()))
print()

print("=== DIRECCION DE LA DERIVA DENTRO DEL EPISODIO ===")
print("  (fraccion de episodios en que el campo sube / baja / mixto)")
for c in ["c3", "c4", "c6", "c7", "c8"]:
    sube = baja = mix = 0
    for _, g in eps:
        s = pd.to_numeric(g[c], errors="coerce").dropna()
        if len(s) < 3:
            continue
        d = np.diff(s.values)
        if (d >= 0).all():
            sube += 1
        elif (d <= 0).all():
            baja += 1
        else:
            mix += 1
    t = max(1, sube + baja + mix)
    print("  %-4s  monot.creciente %5.1f%%   monot.decreciente %5.1f%%   "
          "mixto %5.1f%%" % (c, 100.0 * sube / t, 100.0 * baja / t,
                             100.0 * mix / t))
print()

print("=== c8 CONTRA c3: ¿es c8 el numero de operaciones abiertas? ===")
print("  Si c8 fuese 'operaciones abiertas', al cerrar la ultima deberia")
print("  valer 1 y el registro siguiente ser plano.")
ult = eps.tail(1)
c8u = pd.to_numeric(ult["c8"], errors="coerce")
print("  distribucion de c8 en el ULTIMO registro de cada episodio:")
for k, v in c8u.value_counts().head(8).items():
    print("    c8=%-6.1f %5d  (%.1f%%)" % (k, v, 100.0 * v / len(c8u)))
print()
pri = eps.head(1)
c8p = pd.to_numeric(pri["c8"], errors="coerce")
print("  distribucion de c8 en el PRIMER registro de cada episodio:")
for k, v in c8p.value_counts().head(8).items():
    print("    c8=%-6.1f %5d  (%.1f%%)" % (k, v, 100.0 * v / len(c8p)))
print()

print("=== c6 y c7: ¿contadores acumulados? ===")
for c in ["c0", "c6", "c7"]:
    s = pd.to_numeric(df[c], errors="coerce")
    d = s.diff().dropna()
    print("  %-4s  %% de incrementos >=0: %.1f%%   max valor: %.0f"
          % (c, 100.0 * (d >= 0).mean(), s.max()))
print()

print("=== ¿c9 lleva MAS DE UN instrumento alguna vez? ===")
s9 = df["c9"].astype(str)
multi = s9[s9.str.count(r"[+-]") > 1]
print("  registros con mas de un signo en c9: %d" % len(multi))
if len(multi):
    for v in multi.head(10):
        print("    %r" % v)
print()
print("  valores distintos de c9:")
for k, v in s9.value_counts().items():
    print("    %-34s %5d" % (repr(k)[:34], v))
