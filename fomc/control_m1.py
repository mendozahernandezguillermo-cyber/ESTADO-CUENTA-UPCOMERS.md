#!/usr/bin/env python3
"""
CONTROL POSITIVO DEL FOMC SOBRE DATOS M1  —  prueba de la ganancia de potencia.

En barras DIARIAS medimos el efecto pre-FOMC contra el ruido de la jornada
completa (~141 bp) y salio t=2,57 en 2000-2011 y t=1,82 en 2012-2015.

La aritmetica dice que medirlo en su ventana real deberia multiplicar la t por
~3, porque el ruido de una ventana de pocas horas es una fraccion del diario.
Esto lo comprueba.

Prediccion falsable, hecha ANTES de mirar:
  - 2011-2015 : el efecto debe VERSE con t claramente por encima de 1,82
                (el valor que dio en barras diarias sobre el mismo periodo)
  - 2016-2026 : debe seguir sin verse (la literatura lo da por muerto)
  - la ventana POSTERIOR al anuncio debe ser ruido, no deriva

Detalles que hay que respetar o el test no vale:
  - La hora del anuncio cambio: 14:15 ET hasta 2012, 14:00 ET desde 2013.
  - Los datos de Dukascopy vienen en UTC; hay que pasarlos a hora de Nueva
    York con horario de verano, no con un desplazamiento fijo.
  - Es el indice de contado (CFD), no el futuro. Para ventanas INTRADIA ya
    medimos que la deriva de la base es 1,81 bp/dia, o sea despreciable
    dentro del mismo dia.
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

DIR_M1 = "../nas100-data/raw"

# ---------------------------------------------------------------- fechas
EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
f = f[~f["fecha"].dt.date.isin(EXCLUIR)]
FOMC = set(f["fecha"].dt.date)
print("anuncios del FOMC disponibles: %d" % len(FOMC))

# ---------------------------------------------------------------- M1
print("cargando M1 ...")
trozos = []
for p in sorted(glob.glob("%s/usatechidxusd-m1-*.csv" % DIR_M1)):
    d = pd.read_csv(p, usecols=["timestamp", "close"])
    d["ts"] = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    ny = d["ts"].dt.tz_convert("America/New_York")
    # solo la franja que hace falta, para no cargar 5,6 M de filas
    hm = ny.dt.hour * 60 + ny.dt.minute
    d = d[(hm >= 9 * 60) & (hm <= 16 * 60 + 30)].copy()
    d["dia"] = ny[d.index].dt.date
    d["hm"] = hm[d.index]
    trozos.append(d[["dia", "hm", "close"]])
px = pd.concat(trozos, ignore_index=True).sort_values(["dia", "hm"])
print("filas utiles: %d · dias: %d · %s -> %s"
      % (len(px), px["dia"].nunique(), px["dia"].min(), px["dia"].max()))


def precio_en(g, minuto):
    """ultimo precio en o antes de 'minuto' dentro del dia g."""
    s = g[g["hm"] <= minuto]
    return s["close"].iloc[-1] if len(s) else np.nan


# ---------------------------------------------------------------- snapshots
filas = []
for dia, g in px.groupby("dia", sort=True):
    if len(g) < 200:                       # dia incompleto o festivo
        continue
    anuncio = 14 * 60 + 15 if dia.year <= 2012 else 14 * 60
    filas.append(dict(
        dia=dia,
        p0930=precio_en(g, 9 * 60 + 30),
        p1200=precio_en(g, 12 * 60),
        p_pre=precio_en(g, anuncio),                  # justo antes del anuncio
        p_post=precio_en(g, anuncio + 30),            # 30 min despues
        p1600=precio_en(g, 16 * 60),
    ))
d = pd.DataFrame(filas).dropna()
d["anio"] = pd.to_datetime(d["dia"]).dt.year
d["es_fomc"] = d["dia"].isin(FOMC)

d["w_manana"] = (d["p_pre"] / d["p0930"] - 1) * 1e4     # 09:30 -> anuncio
d["w_2h"] = (d["p_pre"] / d["p1200"] - 1) * 1e4         # 12:00 -> anuncio
d["w_react"] = (d["p_post"] / d["p_pre"] - 1) * 1e4     # anuncio -> +30 min
d["w_tarde"] = (d["p1600"] / d["p_pre"] - 1) * 1e4      # anuncio -> cierre

print("dias con snapshot completo: %d · de ellos FOMC: %d"
      % (len(d), int(d["es_fomc"].sum())))

TRAMOS = [("2011-2015", 2011, 2015), ("2016-2020", 2016, 2020),
          ("2021-2026", 2021, 2026), ("TODO 2011-2026", 2011, 2026)]
VENT = [("w_manana", "09:30 -> anuncio"), ("w_2h", "12:00 -> anuncio"),
        ("w_react", "anuncio -> +30min"), ("w_tarde", "anuncio -> cierre")]

print()
print("=" * 88)
print("EFECTO POR VENTANA INTRADIA  ·  FOMC contra dias normales")
print("=" * 88)
for col, nom in VENT:
    print("\n  %s" % nom)
    print(f"  {'tramo':<16}{'n':>4}{'FOMC':>9}{'otros':>9}{'dif':>8}"
          f"{'sd otros':>10}{'t':>7}{'p':>8}")
    print("  " + "-" * 76)
    for etq, a, b in TRAMOS:
        m = (d["anio"] >= a) & (d["anio"] <= b)
        x = d[col][m & d["es_fomc"]]
        y = d[col][m & ~d["es_fomc"]]
        if len(x) < 8:
            continue
        t, p = stats.ttest_ind(x, y, equal_var=False)
        print(f"  {etq:<16}{len(x):>4}{x.mean():>9.1f}{y.mean():>9.1f}"
              f"{x.mean()-y.mean():>8.1f}{y.std():>10.1f}{t:>7.2f}{p:>8.3f}")

# ------------------------------------------------- la comprobacion clave
print()
print("=" * 88)
print("¿SE CUMPLE LA GANANCIA DE POTENCIA?")
print("=" * 88)
m = (d["anio"] >= 2011) & (d["anio"] <= 2015)
x = d["w_manana"][m & d["es_fomc"]]
y = d["w_manana"][m & ~d["es_fomc"]]
t_m1, _ = stats.ttest_ind(x, y, equal_var=False)
print("  Mismo periodo 2011-2015, mismo efecto, dos resoluciones:")
print("     barras DIARIAS (medido antes) : dif +30.3 bp · sd ~141 bp · t = 1.82")
print("     ventana INTRADIA 09:30-anuncio: dif %+.1f bp · sd ~%.0f bp · t = %.2f"
      % (x.mean() - y.mean(), y.std(), t_m1))
if abs(t_m1) > 1.82:
    print("     -> la t SUBE: la ganancia de potencia es real.")
    print("        factor de mejora: %.1fx" % (abs(t_m1) / 1.82))
else:
    print("     -> la t NO sube. La hipotesis de la ganancia de potencia")
    print("        queda REFUTADA y hay que entender por que.")

# umbral de deteccion nuevo
sd_int = y.std()
print()
print("  Umbral de deteccion con esta resolucion (t=2):")
for n in (35, 60, 100, 200):
    print("     n=%3d eventos -> %.1f bp   (en barras diarias era %.1f bp)"
          % (n, 2 * sd_int / np.sqrt(n), 2 * 141.0 / np.sqrt(n)))

# ------------------------------------------------- perfil por minuto
print()
print("=" * 88)
print("PERFIL MEDIO DEL DIA (bp acumulados desde las 09:30)")
print("=" * 88)
HITOS = [(10 * 60, "10:00"), (11 * 60, "11:00"), (12 * 60, "12:00"),
         (13 * 60, "13:00"), (13 * 60 + 45, "13:45"), (14 * 60, "14:00"),
         (14 * 60 + 30, "14:30"), (15 * 60, "15:00"), (16 * 60, "16:00")]
perf = {}
for dia, g in px.groupby("dia", sort=True):
    if len(g) < 200:
        continue
    base = precio_en(g, 9 * 60 + 30)
    if not base or np.isnan(base):
        continue
    perf[dia] = [(precio_en(g, mm) / base - 1) * 1e4 for mm, _ in HITOS]
P = pd.DataFrame(perf).T
P.columns = [n for _, n in HITOS]
P["anio"] = pd.to_datetime(pd.Series(P.index)).dt.year.values
P["es_fomc"] = pd.Series(P.index).isin(FOMC).values

for etq, a, b in [("2011-2015", 2011, 2015), ("2016-2026", 2016, 2026)]:
    m = (P["anio"] >= a) & (P["anio"] <= b)
    print("\n  %s" % etq)
    print("  %-10s" % "" + "".join("%8s" % n for _, n in HITOS))
    for lab, sel in [("FOMC ", m & P["es_fomc"]), ("otros", m & ~P["es_fomc"])]:
        vals = "".join("%8.1f" % P.loc[sel, n].mean() for _, n in HITOS)
        print("  %-10s%s" % (lab, vals))
