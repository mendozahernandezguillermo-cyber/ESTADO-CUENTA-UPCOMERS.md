#!/usr/bin/env python3
"""
CONTROL POSITIVO DE LA METODOLOGIA.

No busca una estrategia. Contesta a esto: ¿nuestras herramientas detectan un
efecto real cuando lo hay? Llevamos todo el proyecto sin encontrar nada, y eso
admite dos explicaciones que no hemos separado:
    (a) no hay nada donde buscamos
    (b) nuestra maquinaria de medida no detecta efectos

El pre-FOMC drift permite separarlas, porque su historia esta publicada:
    Lucca y Moench (2015): +49 bp en las 24 h previas, sep 1994 - mar 2011
    Boguth et al. (2019)  : solo en anuncios con conferencia de prensa
    'The disappearing...' : practicamente desaparecido despues de 2015

Asi que la prediccion es DOBLE y falsable:
    en 2000-2011 tenemos que VERLO      (~+40/50 bp, significativo)
    en 2016-2026 tenemos que NO verlo   (~0)

Si no sale ese patron, nuestras herramientas estan rotas y todos los
resultados negativos previos no valen nada.

Ventana primaria (declarada ANTES de mirar): cierre(t-1) -> cierre(t) del dia
del anuncio. Se elige porque no usa el precio de apertura, y el control de
calidad mostro que la apertura de Yahoo esta contaminada en varios indices.
La Fed documenta que el precio acaba el dia cerca del nivel previo al anuncio,
asi que esta ventana captura la mayor parte del efecto de 24 h.
"""
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------- fechas
EXCLUIR = {
    # duplicado: la reunion fue 15-16 sep 2003, el anuncio fue el 16
    dt.date(2003, 9, 15),
    # marzo 2020: dos actuaciones de EMERGENCIA (no programadas) y la
    # reunion programada del 17-18 que se CANCELO y no tuvo anuncio
    dt.date(2020, 3, 2), dt.date(2020, 3, 15), dt.date(2020, 3, 18),
    # 22 ago 2025: "notation vote", no es una reunion programada
    dt.date(2025, 8, 22),
}

f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
f["d"] = f["fecha"].dt.date
antes = len(f)
f = f[~f["d"].isin(EXCLUIR)].copy()
# dedupe de dias consecutivos: si dos fechas van seguidas, vale la ultima
f = f.sort_values("d").reset_index(drop=True)
keep = [True] * len(f)
for i in range(1, len(f)):
    if (f["d"].iloc[i] - f["d"].iloc[i - 1]).days <= 1:
        keep[i - 1] = False
f = f[keep].reset_index(drop=True)

print("=" * 82)
print("FECHAS: %d extraidas -> %d tras excluir no programadas y duplicados"
      % (antes, len(f)))
cnt = f.groupby(pd.to_datetime(f["d"]).dt.year).size()
raros = {y: n for y, n in cnt.items() if n != 8 and y != 2026}
print("años con recuento != 8: %s" % (raros if raros else "ninguno"))
print("  (2020 tiene 7 legitimamente: la reunion de marzo se cancelo)")
print("=" * 82)

FECHAS = pd.to_datetime(sorted(f["d"]))

# ---------------------------------------------------------------- precios
def cargar(tk):
    df = pd.read_csv("../nas100-data/yahoo/%s.csv" % tk,
                     index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    df["r_cc"] = df["Close"] / df["Close"].shift(1) - 1.0    # ventana primaria
    return df.dropna()


TRAMOS = [
    ("2000-2011  DOCUMENTADO", 2000, 2011, "deberia VERSE"),
    ("2012-2015  transicion",  2012, 2015, "deberia debilitarse"),
    ("2016-2026  'muerto'",    2016, 2026, "deberia NO verse"),
]

for tk, nom in (("GSPC", "S&P 500"), ("NDX", "NASDAQ 100")):
    px = cargar(tk)
    es_fomc = px.index.normalize().isin(FECHAS)
    print()
    print("=" * 82)
    print("%s · ventana cierre(t-1) -> cierre(t) del dia del anuncio" % nom)
    print("=" * 82)
    print(f"{'tramo':<26}{'n':>5}{'FOMC':>10}{'otros dias':>12}"
          f"{'dif':>9}{'t':>7}{'p':>9}")
    print("-" * 82)
    for etq, a, b, esperado in TRAMOS:
        m = (px.index.year >= a) & (px.index.year <= b)
        rf = px["r_cc"][m & es_fomc] * 1e4
        ro = px["r_cc"][m & ~es_fomc] * 1e4
        if len(rf) < 10:
            continue
        t, p = stats.ttest_ind(rf, ro, equal_var=False)
        print(f"{etq:<26}{len(rf):>5}{rf.mean():>9.1f} "
              f"{ro.mean():>11.1f}{rf.mean()-ro.mean():>9.1f}"
              f"{t:>7.2f}{p:>9.3f}")
    # muestra completa
    t, p = stats.ttest_ind(px["r_cc"][es_fomc] * 1e4,
                           px["r_cc"][~es_fomc] * 1e4, equal_var=False)
    rf = px["r_cc"][es_fomc] * 1e4
    ro = px["r_cc"][~es_fomc] * 1e4
    print("-" * 82)
    print(f"{'TODO 2000-2026':<26}{len(rf):>5}{rf.mean():>9.1f} "
          f"{ro.mean():>11.1f}{rf.mean()-ro.mean():>9.1f}{t:>7.2f}{p:>9.3f}")

# ------------------------------------------------- veredicto del control
print()
print("=" * 82)
print("VEREDICTO DEL CONTROL POSITIVO")
print("=" * 82)
px = cargar("GSPC")
es = px.index.normalize().isin(FECHAS)
def dif(a, b):
    m = (px.index.year >= a) & (px.index.year <= b)
    rf = px["r_cc"][m & es] * 1e4
    ro = px["r_cc"][m & ~es] * 1e4
    t, p = stats.ttest_ind(rf, ro, equal_var=False)
    return rf.mean() - ro.mean(), t, p, len(rf)

d1, t1, p1, n1 = dif(2000, 2011)
d3, t3, p3, n3 = dif(2016, 2026)
print("  2000-2011 : %+.1f bp  (t=%.2f, p=%.3f, n=%d)" % (d1, t1, p1, n1))
print("  2016-2026 : %+.1f bp  (t=%.2f, p=%.3f, n=%d)" % (d3, t3, p3, n3))
print()
detecta = (d1 > 15) and (t1 > 1.5)
muere = abs(d3) < abs(d1)
if detecta and muere:
    v = ("PASA — detectamos el efecto donde esta documentado y su desaparicion\n"
         "  donde la literatura la reporta. Las herramientas funcionan, y por\n"
         "  tanto los resultados negativos anteriores son creibles.")
elif detecta:
    v = ("PARCIAL — detectamos el efecto historico pero no su desaparicion.\n"
         "  Las herramientas miden; la cronologia no encaja con la literatura.")
else:
    v = ("FALLA — no detectamos un efecto de +49 bp que esta publicado y\n"
         "  replicado. La maquinaria de medida no sirve, y ningun resultado\n"
         "  negativo anterior es interpretable hasta arreglarla.")
print("  %s" % v)
