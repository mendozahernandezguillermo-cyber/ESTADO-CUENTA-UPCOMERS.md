#!/usr/bin/env python3
"""
GENERA EL BLOQUE DE CIERRES MENSUALES DE REFERENCIA PARA EA_Trend_Multi.

PROBLEMA: el broker no tiene datos antes del 12 de enero de 2026. La señal
necesita el cierre de hace 13 meses. No hay forma de sacarlo del terminal.

SOLUCION: se empalman dos series. Los meses recientes vienen del broker y los
antiguos de aqui, reescalados para que casen en el mes de solape:

    factor = P_broker[solape] / P_ref[solape]
    P[t] = P_broker[t]            si t >= solape
    P[t] = P_ref[t] * factor      si t <  solape
    señal = signo( P[-1] / P[-13] - 1 )

El reescalado hace que el NIVEL de precio no importe: SPY cotiza a ~1/10 del
S&P y GLD a ~1/10 de la onza de oro, y da igual, porque solo se usan
cocientes. Eso es lo que permite mezclar un ETF con un CFD.

Y se auto-obsoletiza: cuando el broker acumule 14 meses (marzo de 2027) el
empalme deja de usarse solo, sin tocar nada.

LO QUE SE CONCEDE, dicho claro: SPY y QQQ vienen ajustados por dividendos y
el CFD sobre indice no, asi que la pata antigua del cociente lleva el
dividendo dentro (~1,3% anual en el S&P). Solo cambiaria el SIGNO si el
retorno de 12 meses estuviera a menos de eso de cero.
"""
import numpy as np
import pandas as pd

CESTA = [
    ("SPCUSD.c", "datos/SPY.csv"),
    ("NACUSD.c", "datos/QQQ.csv"),
    ("XAUUSD",   "datos/GLD.csv"),
    ("XAGUSD",   "datos/SLV.csv"),
    ("EURUSD",   "datos/EURUSDX.csv"),
    ("USDJPY",   "datos/USDJPYX.csv"),
    ("GBPUSD",   "datos/GBPUSDX.csv"),
    ("AUDUSD",   "datos/AUDUSDX.csv"),
]
DESDE = "2023-12-01"          # margen de sobra por delante de la señal

mensuales = {}
for nom, p in CESTA:
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    s = s[s > 0]
    m = s.resample("ME").last().dropna()
    m = m[m.index >= DESDE]
    mensuales[nom] = m

# rejilla comun de meses
meses = sorted(set.intersection(*[set(v.index) for v in mensuales.values()]))
aniomes = [d.year * 100 + d.month for d in meses]

print("=" * 78)
print("CIERRES MENSUALES DE REFERENCIA")
print("=" * 78)
print(f"  {len(meses)} meses  ·  {meses[0].date()} -> {meses[-1].date()}")
print(f"  {len(CESTA)} mercados  ·  {len(CESTA)*len(meses)} valores")
print()
print(f"  {'mes':>8}", end="")
for nom, _ in CESTA:
    print(f"{nom.replace('.c',''):>10}", end="")
print()
print("  " + "-" * (8 + 10 * len(CESTA)))
for i, d in enumerate(meses):
    print(f"  {aniomes[i]:>8}", end="")
    for nom, _ in CESTA:
        print(f"{mensuales[nom].loc[d]:>10.4f}", end="")
    print()

# ---------------------------------------------------- bloque MQL5
lineas = []
lineas.append("//--- Cierres mensuales de REFERENCIA para empalmar la señal.")
lineas.append("//    Generado por trend/generar_referencia.py.")
lineas.append("//    %d meses x %d mercados. Solo se usan COCIENTES, asi que el"
              % (len(meses), len(CESTA)))
lineas.append("//    nivel de precio de la fuente es irrelevante.")
lineas.append("#define REF_MESES     %d" % len(meses))
lineas.append("#define REF_MERCADOS  %d" % len(CESTA))
lineas.append("")
lineas.append("int REF_ANIOMES[REF_MESES] =")
lineas.append("  {")
for i in range(0, len(aniomes), 12):
    lineas.append("   " + ", ".join(str(x) for x in aniomes[i:i + 12]) +
                  ("," if i + 12 < len(aniomes) else ""))
lineas.append("  };")
lineas.append("")
lineas.append("string REF_SIMBOLO[REF_MERCADOS] =")
lineas.append("  {")
lineas.append("   " + ", ".join('"%s"' % n for n, _ in CESTA))
lineas.append("  };")
lineas.append("")
lineas.append("//--- indice = mercado * REF_MESES + mes")
lineas.append("double REF_CIERRE[REF_MERCADOS * REF_MESES] =")
lineas.append("  {")
for k, (nom, _) in enumerate(CESTA):
    vals = [mensuales[nom].loc[d] for d in meses]
    txt = ", ".join(f"{v:.4f}" for v in vals)
    coma = "," if k < len(CESTA) - 1 else ""
    lineas.append(f"   // {nom}")
    for i in range(0, len(vals), 8):
        trozo = ", ".join(f"{v:.4f}" for v in vals[i:i + 8])
        fin = "," if (i + 8 < len(vals) or k < len(CESTA) - 1) else ""
        lineas.append("   " + trozo + fin)
lineas.append("  };")

bloque = "\n".join(lineas)
open("referencia_mql5.txt", "w", encoding="utf-8").write(bloque)
print()
print("=" * 78)
print("bloque MQL5 escrito en trend/referencia_mql5.txt  (%d lineas)"
      % len(lineas))
print("=" * 78)

# ---------------------------------------------------- control: la señal de hoy
print()
print("CONTROL: señal que debe salir en el rebalanceo de septiembre 2026")
print("-" * 78)
print(f"  {'mercado':<11}{'mes -1':>9}{'mes -13':>10}{'ret 12m':>10}{'señal':>7}")
print("  " + "-" * 47)
for nom, _ in CESTA:
    m = mensuales[nom]
    if len(m) < 13:
        continue
    p1, p13 = m.iloc[-1], m.iloc[-13]
    r = p1 / p13 - 1
    print(f"  {nom:<11}{p1:>9.4f}{p13:>10.4f}{r:>+9.1%}"
          f"{(1 if r >= 0 else -1):>7}")
