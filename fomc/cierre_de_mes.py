#!/usr/bin/env python3
"""
EFECTO DE CIERRE DE MES Y DE TRIMESTRE (turn-of-the-month).

Mecanismo alegado: flujos FORZADOS de fin de mes — aportaciones a planes de
pensiones, rebalanceo de fondos indexados, nominas. Es la clase de efecto que
puede sobrevivir a ser conocido, porque alguien tiene que operar en esa fecha
lo sepa quien lo sepa.

HIPOTESIS DECLARADA ANTES DE MIRAR (especificacion estandar de la literatura,
McConnell y Xu): la ventana de cierre de mes son los dias de mercado
    -1 (ultimo del mes) y +1, +2, +3 (primeros del mes siguiente)

UNA sola hipotesis. Varios instrumentos y varios periodos son CONFIRMACION,
no busqueda. El oro es control negativo.

Y la distincion que decide si sirve para una cuenta prop de futuros:
    cierre->cierre  = efecto total, exige aguantar de un dia para otro
    apertura->cierre = tramo INTRADIA, el unico compatible con plano al cierre
Solo se usan indices cuya apertura de Yahoo paso el control de calidad
(NASDAQ 0,7% · DAX 0,1% · Nikkei 0,0% · oro 2,8%). El S&P se incluye solo en
cierre->cierre, que no usa la apertura.

Umbral de deteccion calibrado en el control positivo del FOMC:
    efecto minimo detectable ~ 282/raiz(n) bp por evento
"""
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"

# (ticker, nombre, apertura fiable?)
INSTR = [
    ("NDX",   "NASDAQ 100",  True),
    ("GSPC",  "S&P 500",     False),
    ("GDAXI", "DAX",         True),
    ("N225",  "Nikkei 225",  True),
    ("GCF",   "Oro CONTROL", True),
]
TRAMOS = [("2000-2011", 2000, 2011), ("2012-2019", 2012, 2019),
          ("2020-2026", 2020, 2026)]


def cargar(tk):
    df = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    df["r_cc"] = df["Close"] / df["Close"].shift(1) - 1.0
    df["r_oc"] = df["Close"] / df["Open"] - 1.0
    df = df.dropna()

    # posicion del dia de mercado dentro del mes
    g = df.groupby([df.index.year, df.index.month])
    df["pos_ini"] = g.cumcount() + 1                       # 1 = primer dia
    df["pos_fin"] = g.cumcount(ascending=False) + 1        # 1 = ultimo dia
    # etiqueta de ventana: -1 el ultimo del mes; +1..+3 los primeros
    df["tom"] = ((df["pos_fin"] == 1) | (df["pos_ini"] <= 3))
    df["tom_dia"] = np.where(df["pos_fin"] == 1, -1,
                             np.where(df["pos_ini"] <= 3, df["pos_ini"], 0))
    # trimestre: cierre de marzo, junio, septiembre y diciembre
    df["fin_trim"] = (df["pos_fin"] == 1) & df.index.month.isin([3, 6, 9, 12])
    df["tom_trim"] = df["tom"] & (
        ((df["pos_fin"] == 1) & df.index.month.isin([3, 6, 9, 12])) |
        ((df["pos_ini"] <= 3) & df.index.month.isin([4, 7, 10, 1])))
    return df


def contrasta(df, mask, col, a, b):
    m = (df.index.year >= a) & (df.index.year <= b)
    x = df[col][m & mask] * 1e4
    y = df[col][m & ~mask] * 1e4
    if len(x) < 15:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return dict(n=len(x), mx=x.mean(), my=y.mean(),
                dif=x.mean() - y.mean(), t=t, p=p)


# ============================================= 1. efecto total (cierre->cierre)
print("=" * 88)
print("1. VENTANA DE CIERRE DE MES (-1, +1, +2, +3)  ·  CIERRE -> CIERRE")
print("   [efecto total; exige aguantar de un dia para otro]")
print("=" * 88)
print(f"{'indice':<14}{'tramo':<11}{'n':>5}{'ventana':>10}{'resto':>9}"
      f"{'dif':>8}{'t':>7}{'p':>8}")
print("-" * 88)
for tk, nom, _ in INSTR:
    df = cargar(tk)
    for etq, a, b in TRAMOS:
        r = contrasta(df, df["tom"], "r_cc", a, b)
        if r:
            print(f"{nom:<14}{etq:<11}{r['n']:>5}{r['mx']:>10.1f}"
                  f"{r['my']:>9.1f}{r['dif']:>8.1f}{r['t']:>7.2f}{r['p']:>8.3f}")
    print()

# ============================================= 2. solo el tramo INTRADIA
print("=" * 88)
print("2. LA MISMA VENTANA  ·  APERTURA -> CIERRE")
print("   [tramo intradia: el UNICO compatible con plano al cierre en prop]")
print("=" * 88)
print(f"{'indice':<14}{'tramo':<11}{'n':>5}{'ventana':>10}{'resto':>9}"
      f"{'dif':>8}{'t':>7}{'p':>8}")
print("-" * 88)
for tk, nom, ok_open in INSTR:
    if not ok_open:
        continue
    df = cargar(tk)
    for etq, a, b in TRAMOS:
        r = contrasta(df, df["tom"], "r_oc", a, b)
        if r:
            print(f"{nom:<14}{etq:<11}{r['n']:>5}{r['mx']:>10.1f}"
                  f"{r['my']:>9.1f}{r['dif']:>8.1f}{r['t']:>7.2f}{r['p']:>8.3f}")
    print()

# ============================================= 3. dia a dia (descriptivo)
print("=" * 88)
print("3. DESGLOSE POR DIA DE LA VENTANA  (descriptivo, NO son 4 pruebas)")
print("   valor = bp medios; cc = cierre a cierre, oc = intradia")
print("=" * 88)
print(f"{'indice':<14}" + "".join(f"{d:>16}" for d in
                                  ["-1 (ult.mes)", "+1", "+2", "+3"]))
print("-" * 88)
for tk, nom, ok_open in INSTR:
    df = cargar(tk)
    fila = ""
    for d in (-1, 1, 2, 3):
        m = df["tom_dia"] == d
        cc = df["r_cc"][m].mean() * 1e4
        oc = df["r_oc"][m].mean() * 1e4 if ok_open else np.nan
        fila += f"{('%+.0f/%+.0f' % (cc, oc)) if ok_open else ('%+.0f/  -' % cc):>16}"
    print(f"{nom:<14}{fila}")

# ============================================= 4. cierre de TRIMESTRE
print()
print("=" * 88)
print("4. SOLO CIERRE DE TRIMESTRE  (flujos mayores, pero n mas pequeño)")
print("=" * 88)
print(f"{'indice':<14}{'ventana':<10}{'n':>5}{'dif cc':>9}{'t':>7}"
      f"{'dif oc':>9}{'t':>7}{'min.det.':>10}")
print("-" * 88)
for tk, nom, ok_open in INSTR:
    df = cargar(tk)
    r1 = contrasta(df, df["tom_trim"], "r_cc", 2000, 2026)
    r2 = contrasta(df, df["tom_trim"], "r_oc", 2000, 2026) if ok_open else None
    if r1:
        det = 282.0 / np.sqrt(r1["n"])
        print(f"{nom:<14}{'trimestre':<10}{r1['n']:>5}{r1['dif']:>9.1f}"
              f"{r1['t']:>7.2f}"
              f"{(r2['dif'] if r2 else np.nan):>9.1f}"
              f"{(r2['t'] if r2 else np.nan):>7.2f}{det:>10.1f}")

# ============================================= 5. veredicto
print()
print("=" * 88)
print("5. VEREDICTO")
print("=" * 88)
reales = [i for i in INSTR if i[1] != "Oro CONTROL"]
print("  Recuento sobre los 4 indices de renta variable, muestra completa:")
for col, etq in (("r_cc", "cierre->cierre"), ("r_oc", "intradia")):
    pos = sig = tot = 0
    for tk, nom, ok in reales:
        if col == "r_oc" and not ok:
            continue
        r = contrasta(cargar(tk), cargar(tk)["tom"], col, 2000, 2026)
        if r:
            tot += 1
            pos += r["dif"] > 0
            sig += r["t"] > 2.0
    print("    %-16s dif>0 en %d/%d · t>2 en %d/%d" % (etq, pos, tot, sig, tot))
r = contrasta(cargar("GCF"), cargar("GCF")["tom"], "r_cc", 2000, 2026)
print("  CONTROL (oro), cierre->cierre: %+.1f bp, t=%.2f -> %s"
      % (r["dif"], r["t"], "falla, BIEN" if abs(r["t"]) < 2 else "TAMBIEN dispara"))
