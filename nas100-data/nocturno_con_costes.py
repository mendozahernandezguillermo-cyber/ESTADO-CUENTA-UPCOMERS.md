#!/usr/bin/env python3
"""
¿SOBREVIVE EL TRAMO NOCTURNO A LOS COSTES REALES DE UN CFD?

La estrategia: comprar al cierre, vender a la apertura siguiente. Todos los
dias. Tres costes, y el primero se me habia pasado en el analisis anterior:

  1. FINANCIACION (swap). Una posicion overnight en CFD la paga. Medida en el
     broker real: 4,56% anual -> 4,56/365 = 1,249 bp por noche de calendario.
     El paso de viernes a lunes son TRES noches -> 3,75 bp.
     Esto ataca al tramo nocturno de forma directa y proporcional.

  2. SPREAD, ida y vuelta. Y el detalle que empeora las cosas: el nocturno
     obliga a operar en la apertura y en el cierre, los dos momentos con el
     spread MAS ANCHO del dia.

  3. La regla de no aguantar el fin de semana, si aplica.

Referencia bruta medida antes (bp por sesion):
    Nikkei 4,55 · Oro 4,55 · NASDAQ 3,44 · S&P 3,35 · DAX 2,97 · Dow 0,52
"""
import os
import numpy as np
import pandas as pd

DIR = "yahoo"
SWAP_ANUAL = 0.0456
BP_POR_NOCHE = SWAP_ANUAL / 365.0 * 1e4        # 1,249 bp

INSTR = {
    "NDX":   ("NASDAQ 100",   None),
    "GSPC":  ("S&P 500",      2016),
    "DJI":   ("Dow 30",       None),
    "RUT":   ("Russell 2000", 2011),
    "GDAXI": ("DAX",          None),
    "N225":  ("Nikkei 225",   None),
    "GCF":   ("Oro futuro",   None),
}

# spread de ida (bp). round trip = 2x
SPREADS = {
    "futuro E-mini":      0.30,
    "CFD estrecho":       0.75,
    "CFD tipico":         1.50,
    "CFD en apertura":    2.50,
}


def cargar(tk, desde):
    df = pd.read_csv(os.path.join(DIR, "%s.csv" % tk),
                     index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    if desde:
        df = df[df.index.year >= desde]
    d = pd.DataFrame(index=df.index)
    d["bruto"] = (df["Open"] / df["Close"].shift(1) - 1.0) * 1e4
    # noches de calendario que se aguanta la posicion
    d["noches"] = df.index.to_series().diff().dt.days
    d["dow"] = df.index.dayofweek          # 0=lunes
    d = d.dropna()
    d = d[(d["bruto"].abs() < 1500) & (d["noches"] >= 1) & (d["noches"] <= 5)]
    return d


def sharpe(r, n_por_ano):
    if len(r) < 100 or r.std() == 0:
        return np.nan
    return r.mean() / r.std() * np.sqrt(n_por_ano)


# ===================================================== 1. por dia de la semana
print("=" * 88)
print("1. RETORNO NOCTURNO BRUTO POR NOCHE, SEGUN EL DIA EN QUE SE ABRE")
print("   (la noche del viernes son 3 noches de calendario -> triple swap)")
print("=" * 88)
DOW = {0: "lun->mar", 1: "mar->mie", 2: "mie->jue", 3: "jue->vie", 4: "vie->lun"}
print(f"{'indice':<15}" + "".join(f"{DOW[i]:>13}" for i in range(5)))
print("-" * 88)
for tk, (nom, desde) in INSTR.items():
    d = cargar(tk, desde)
    # el dow guardado es el del dia de APERTURA; la posicion se abrio el
    # dia de mercado anterior, asi que se mira el dow del cierre previo
    d["dow_apertura"] = (d["dow"] - d["noches"].clip(upper=3).astype(int)) % 7
    fila = ""
    for i in range(5):
        m = d.index.dayofweek == (i + 1) % 7 if i < 4 else d.index.dayofweek == 0
        fila += f"{d['bruto'][m].mean():>12.2f} " if m.sum() > 50 else f"{'n/d':>13}"
    print(f"{nom:<15}{fila}")
print()
print("La ultima columna es la noche del fin de semana: 3 noches de swap.")

# ===================================================== 2. neto tras costes
print()
print("=" * 88)
print("2. RETORNO NETO TRAS FINANCIACION Y SPREAD  (bp por operacion)")
print("   financiacion = 1,249 bp x noches de calendario")
print("=" * 88)
for etq, sp in SPREADS.items():
    print(f"\n  --- spread de ida {sp:.2f} bp (ida y vuelta {2*sp:.2f}) · {etq} ---")
    print(f"  {'indice':<15}{'bruto':>9}{'financ.':>9}{'spread':>9}"
          f"{'NETO':>9}{'Sharpe neto':>13}{'ops/ano':>9}")
    print("  " + "-" * 82)
    for tk, (nom, desde) in INSTR.items():
        d = cargar(tk, desde).copy()
        fin = d["noches"] * BP_POR_NOCHE
        d["neto"] = d["bruto"] - fin - 2 * sp
        anos = (d.index.max() - d.index.min()).days / 365.25
        n_ano = len(d) / anos
        print(f"  {nom:<15}{d['bruto'].mean():>9.2f}{-fin.mean():>9.2f}"
              f"{-2*sp:>9.2f}{d['neto'].mean():>9.2f}"
              f"{sharpe(d['neto'], n_ano):>13.2f}{n_ano:>9.0f}")

# ============================================ 3. sin aguantar el fin de semana
print()
print("=" * 88)
print("3. EFECTO DE NO AGUANTAR EL FIN DE SEMANA")
print("   (se salta la posicion que cruzaria el sabado y el domingo)")
print("=" * 88)
sp = 0.75
print(f"  spread de ida {sp} bp · CFD estrecho")
print(f"  {'indice':<15}{'TODAS las noches':>26}{'SIN fin de semana':>26}")
print(f"  {'':<15}{'neto':>10}{'Sharpe':>9}{'ops':>7}"
      f"{'neto':>10}{'Sharpe':>9}{'ops':>7}")
print("  " + "-" * 82)
for tk, (nom, desde) in INSTR.items():
    d = cargar(tk, desde).copy()
    d["neto"] = d["bruto"] - d["noches"] * BP_POR_NOCHE - 2 * sp
    anos = (d.index.max() - d.index.min()).days / 365.25
    sinfs = d[d["noches"] <= 1]
    print(f"  {nom:<15}{d['neto'].mean():>10.2f}"
          f"{sharpe(d['neto'], len(d)/anos):>9.2f}{len(d)/anos:>7.0f}"
          f"{sinfs['neto'].mean():>10.2f}"
          f"{sharpe(sinfs['neto'], len(sinfs)/anos):>9.2f}"
          f"{len(sinfs)/anos:>7.0f}")

# ==================================================== 4. umbral de rentabilidad
print()
print("=" * 88)
print("4. SPREAD MAXIMO TOLERABLE (ida, en bp) PARA QUE EL NETO SIGA > 0")
print("=" * 88)
print(f"  {'indice':<15}{'todas las noches':>20}{'sin fin de semana':>20}")
print("  " + "-" * 82)
for tk, (nom, desde) in INSTR.items():
    d = cargar(tk, desde)
    def umbral(x):
        if len(x) < 100:
            return np.nan
        return (x["bruto"].mean() - (x["noches"] * BP_POR_NOCHE).mean()) / 2.0
    u_all = umbral(d)
    u_sin = umbral(d[d["noches"] <= 1])
    print(f"  {nom:<15}{u_all:>20.2f}{u_sin:>20.2f}")
print()
print("  Referencia: un CFD de indice raramente baja de 0,5-0,8 bp de ida, y en")
print("  la apertura y el cierre esta mas cerca de 1,5-2,5 bp. Un futuro")
print("  E-mini ronda 0,3 bp pero NO se puede aguantar overnight en prop.")
