#!/usr/bin/env python3
"""
GENERALIZACION: ¿existe la prima nocturna antes de OTROS eventos programados?

Si el mecanismo del hueco pre-FOMC es una prima por aguantar la incertidumbre
de un evento con fecha y hora fijas, tiene que aparecer tambien antes del IPC y
del informe de empleo. Eso serviria para dos cosas:
   - seria el mecanismo (tres eventos independientes, no un condicionante)
   - multiplicaria los eventos de 8 a ~32 al año, que arregla la irregularidad
     de la trayectoria y el problema del apalancamiento

PROBLEMA DE DATOS: el BLS bloquea la descarga automatica (403). En vez de
aproximar las fechas con reglas de calendario (que meteria ruido), se
IDENTIFICAN por su firma en los precios: una publicacion a las 8:30 ET produce
un salto de volatilidad inconfundible en ese minuto.

Y no hay circularidad: la ventana que se prueba es 16:00 -> 08:30, que termina
ANTES del salto que se usa para identificar el dia. Son ventanas disjuntas.

Etapas:
  1. Verificar que el salto de las 8:30 es detectable
  2. Identificar los dias de publicacion por ese salto
  3. Contrastar las fechas identificadas con las reglas de calendario conocidas
     (empleo: primer viernes; IPC: mitad de mes) como control de cordura
  4. Medir la ventana 16:00 -> 08:30 en esos dias
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

DIR_M1 = "../nas100-data/raw"

print("cargando M1 en las franjas necesarias ...")
tr = []
for p in sorted(glob.glob("%s/usatechidxusd-m1-*.csv" % DIR_M1)):
    d = pd.read_csv(p, usecols=["timestamp", "close"])
    ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    ny = ts.dt.tz_convert("America/New_York")
    hm = ny.dt.hour * 60 + ny.dt.minute
    # 15:50-16:05 (cierre de contado) y 07:00-09:40 (pre-apertura y 8:30)
    keep = ((hm >= 15 * 60 + 50) & (hm <= 16 * 60 + 5)) | \
           ((hm >= 7 * 60) & (hm <= 9 * 60 + 40))
    d = d[keep]
    tr.append(pd.DataFrame({"dia": ny[keep].dt.date, "hm": hm[keep],
                            "px": d["close"].values}))
S = pd.concat(tr, ignore_index=True).drop_duplicates(["dia", "hm"])
piv = S.pivot(index="dia", columns="hm", values="px").sort_index()
cols = np.array(piv.columns)
print("dias: %d · %s -> %s" % (len(piv), piv.index.min(), piv.index.max()))


def px(fila, minuto):
    v = cols[cols <= minuto]
    for c in v[::-1]:
        x = fila.get(c, np.nan)
        if pd.notna(x):
            return x
    return np.nan


M830, M825, M835 = 8 * 60 + 30, 8 * 60 + 25, 8 * 60 + 35
filas = []
for dia, fila in piv.iterrows():
    p825, p835, p830 = px(fila, M825), px(fila, M835), px(fila, M830)
    p1600 = px(fila, 16 * 60)
    if any(pd.isna(v) for v in (p825, p835, p830)):
        continue
    filas.append(dict(dia=dia, salto=abs(p835 / p825 - 1) * 1e4,
                      p830=p830, p1600=p1600))
d = pd.DataFrame(filas)
d["fecha"] = pd.to_datetime(d["dia"])
d["dow"] = d["fecha"].dt.dayofweek
d["dom"] = d["fecha"].dt.day
d = d[d["salto"].notna()]

# ============================================== 1. ¿se detecta el salto?
print()
print("=" * 86)
print("1. ¿ES DETECTABLE EL SALTO DE LAS 8:30 ET?")
print("   |retorno 08:25 -> 08:35| en bp, por dia del mes")
print("=" * 86)
med = d["salto"].median()
print("  mediana global del salto: %.1f bp" % med)
print()
print("  dias del mes con salto mediano mas alto:")
por_dom = d.groupby("dom")["salto"].agg(["median", "count"])
for dom, r in por_dom.sort_values("median", ascending=False).head(8).iterrows():
    print("     dia %2d: mediana %5.1f bp  (n=%d)  %s"
          % (dom, r["median"], r["count"],
             "#" * int(r["median"] / med * 10)))
print()
print("  por dia de la semana:")
for dw, nom in enumerate(["lunes", "martes", "miercoles", "jueves", "viernes"]):
    s = d[d["dow"] == dw]["salto"]
    print("     %-10s mediana %5.1f bp (n=%d)" % (nom, s.median(), len(s)))

# ============================================== 2. identificar los dias
UMBRAL = d["salto"].quantile(0.90)
print()
print("=" * 86)
print("2. IDENTIFICACION DE DIAS DE PUBLICACION")
print("=" * 86)
print("  umbral = percentil 90 del salto = %.1f bp" % UMBRAL)
d["pub"] = d["salto"] >= UMBRAL

# empleo: viernes con salto grande, primer viernes del mes
d["es_viernes"] = d["dow"] == 4
vie = d[d["es_viernes"]]
prim_vie = vie.groupby([vie["fecha"].dt.year,
                        vie["fecha"].dt.month])["dia"].min()
d["primer_viernes"] = d["dia"].isin(set(prim_vie.values))
# ipc: dia habil entre el 9 y el 16 con el mayor salto del mes
cand_ipc = d[(d["dom"] >= 9) & (d["dom"] <= 16)]
idx_ipc = cand_ipc.groupby([cand_ipc["fecha"].dt.year,
                            cand_ipc["fecha"].dt.month])["salto"].idxmax()
d["ipc"] = d.index.isin(idx_ipc)
# empleo: primer viernes; si su salto es bajo, se prueba el segundo viernes
d["empleo"] = d["primer_viernes"]

print()
print("  CONTROL DE CORDURA — ¿tienen salto grande los dias identificados?")
print(f"  {'grupo':<28}{'n':>6}{'salto mediano':>16}{'% sobre umbral':>16}")
print("  " + "-" * 68)
for nom, m in [("primer viernes (empleo)", d["empleo"]),
               ("mitad de mes (IPC)", d["ipc"]),
               ("resto de dias", ~(d["empleo"] | d["ipc"]))]:
    s = d[m]
    print(f"  {nom:<28}{len(s):>6}{s['salto'].median():>16.1f}"
          f"{100.0 * s['pub'].mean():>15.0f}%")

# ============================================== 3. la ventana previa
print()
print("=" * 86)
print("3. VENTANA 16:00(dia anterior) -> 08:30  ·  ANTES de la publicacion")
print("=" * 86)
d = d.sort_values("dia").reset_index(drop=True)
d["p1600_prev"] = d["p1600"].shift(1)
d["dias_sep"] = (d["fecha"] - d["fecha"].shift(1)).dt.days
v = d[(d["dias_sep"].between(1, 5)) & d["p1600_prev"].notna()].copy()
v["prev"] = (v["p830"] / v["p1600_prev"] - 1) * 1e4
v = v[v["prev"].abs() < 1000]
print("  ventanas validas: %d" % len(v))
print()
print(f"  {'grupo':<26}{'n':>6}{'media':>9}{'resto':>9}{'dif':>8}"
      f"{'t':>7}{'p':>8}")
print("  " + "-" * 68)
base = v[~(v["empleo"] | v["ipc"])]["prev"]
for nom, m in [("EMPLEO (primer viernes)", v["empleo"]),
               ("IPC (mitad de mes)", v["ipc"]),
               ("los dos juntos", v["empleo"] | v["ipc"])]:
    x = v["prev"][m]
    t, p = stats.ttest_ind(x, base, equal_var=False)
    print(f"  {nom:<26}{len(x):>6}{x.mean():>9.1f}{base.mean():>9.1f}"
          f"{x.mean()-base.mean():>8.1f}{t:>7.2f}{p:>8.3f}")

print()
print("  Referencia: el hueco pre-FOMC (16:00 -> 09:30) dio +22,3 bp, t=3,76")

# ============================================== 4. veredicto
print()
print("=" * 86)
print("4. VEREDICTO")
print("=" * 86)
x = v["prev"][v["empleo"] | v["ipc"]]
t, p = stats.ttest_ind(x, base, equal_var=False)
print("  Prima previa a IPC y empleo: %+.1f bp · t=%.2f · n=%d"
      % (x.mean() - base.mean(), t, len(x)))
print()
if abs(t) > 2.24 and x.mean() > base.mean():
    print("  GENERALIZA -> hay mecanismo de prima por evento programado, y")
    print("  los eventos pasan de 8 a ~%d al año." % int(len(x) / 15))
else:
    print("  NO GENERALIZA. La prima previa no aparece antes del IPC ni del")
    print("  empleo, asi que la hipotesis de 'prima por evento programado'")
    print("  queda descartada: lo del FOMC es especifico del FOMC, y sigue")
    print("  sin mecanismo conocido. Tampoco se multiplican los eventos.")
