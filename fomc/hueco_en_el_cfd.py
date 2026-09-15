#!/usr/bin/env python3
"""
EL HUECO PRE-FOMC MEDIDO EN EL INSTRUMENTO OPERABLE.

Lo anterior estaba medido en el indice de CONTADO de Yahoo: +21,8 bp de media
con t=3,74 sobre 212 eventos. Pero el contado no se opera. Y en este proyecto
ya nos costo caro confundir las dos cosas: NACUSD.c se separo del indice hasta
+259,5 puntos y eso invalido quince años de backtest.

Aqui se mide sobre el CFD del NASDAQ (Dukascopy M1, 2011-2026), que cotiza en
CONTINUO durante la ventana nocturna. La pregunta no es si el movimiento
existe, es si se captura manteniendo una posicion real desde el cierre del
contado (16:00 ET) hasta su apertura (09:30 ET).

Y una pregunta añadida que puede mejorar la economia: ¿DONDE dentro de esas
17,5 horas ocurre el movimiento? Si esta concentrado, se aguanta menos tiempo,
se paga menos swap y se reduce la exposicion.
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

DIR_M1 = "../nas100-data/raw"
SWAP_HORA = 0.0456 / 365.0 / 24.0 * 1e4      # bp por hora de posicion

EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)

print("cargando M1 y muestreando cada 15 min ...")
tr = []
for p in sorted(glob.glob("%s/usatechidxusd-m1-*.csv" % DIR_M1)):
    d = pd.read_csv(p, usecols=["timestamp", "close"])
    ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    ny = ts.dt.tz_convert("America/New_York")
    keep = (ny.dt.minute % 15 == 0)
    d = d[keep]
    tr.append(pd.DataFrame({"dia": ny[keep].dt.date,
                            "hm": ny[keep].dt.hour * 60 + ny[keep].dt.minute,
                            "px": d["close"].values}))
S = pd.concat(tr, ignore_index=True).drop_duplicates(["dia", "hm"])
S = S.sort_values(["dia", "hm"]).reset_index(drop=True)
print("puntos: %d · dias naturales: %d" % (len(S), S["dia"].nunique()))

# tabla dia x hora
piv = S.pivot(index="dia", columns="hm", values="px").sort_index()

# sesiones = dias con datos en horario de contado
CIERRE, APERTURA = 16 * 60, 9 * 60 + 30
cols = np.array(piv.columns)


def px_en(fila, minuto):
    """ultimo precio disponible en o antes de 'minuto' en esa fila."""
    validos = cols[(cols <= minuto)]
    for c in validos[::-1]:
        v = fila.get(c, np.nan)
        if pd.notna(v):
            return v
    return np.nan


ses = []
for dia, fila in piv.iterrows():
    n = fila[(cols >= APERTURA) & (cols <= CIERRE)].notna().sum()
    if n >= 20:
        ses.append(dia)
ses = pd.Index(ses)
print("sesiones validas: %d · %s -> %s" % (len(ses), ses.min(), ses.max()))

# ---------------------------------------------- hueco y perfil nocturno
HITOS = [(CIERRE, "16:00"), (17 * 60, "17:00"), (19 * 60, "19:00"),
         (21 * 60, "21:00"), (23 * 60, "23:00")]
HITOS_D = [(1 * 60, "01:00"), (3 * 60, "03:00"), (5 * 60, "05:00"),
           (7 * 60, "07:00"), (8 * 60 + 30, "08:30"), (9 * 60, "09:00"),
           (APERTURA, "09:30")]

filas = []
for i in range(1, len(ses)):
    hoy, ayer = ses[i], ses[i - 1]
    if (hoy - ayer).days > 5:
        continue
    fa, fh = piv.loc[ayer], piv.loc[hoy]
    base = px_en(fa, CIERRE)
    ap = px_en(fh, APERTURA)
    if not (base and ap) or np.isnan(base) or np.isnan(ap):
        continue
    r = dict(dia=hoy, noches=(hoy - ayer).days,
             hueco=(ap / base - 1) * 1e4, es_fomc=hoy in FOMC)
    for mm, nom in HITOS:
        v = px_en(fa, mm)
        r["c_" + nom] = (v / base - 1) * 1e4 if pd.notna(v) else np.nan
    for mm, nom in HITOS_D:
        v = px_en(fh, mm)
        r["c_" + nom] = (v / base - 1) * 1e4 if pd.notna(v) else np.nan
    filas.append(r)

d = pd.DataFrame(filas)
d["anio"] = pd.to_datetime(d["dia"]).dt.year
print("ventanas nocturnas construidas: %d · de ellas FOMC: %d"
      % (len(d), int(d["es_fomc"].sum())))

# ============================================================ 1. el hueco
print()
print("=" * 88)
print("1. HUECO 16:00 -> 09:30 EN EL CFD  ·  FOMC contra el resto")
print("=" * 88)
print(f"{'tramo':<14}{'n':>5}{'FOMC':>9}{'resto':>8}{'dif':>8}"
      f"{'sd FOMC':>10}{'t':>7}{'p':>8}")
print("-" * 88)
for etq, a, b in [("2011-2015", 2011, 2015), ("2016-2020", 2016, 2020),
                  ("2021-2026", 2021, 2026), ("TODO", 2011, 2026)]:
    m = (d["anio"] >= a) & (d["anio"] <= b)
    x, y = d["hueco"][m & d["es_fomc"]], d["hueco"][m & ~d["es_fomc"]]
    if len(x) < 8:
        continue
    t, p = stats.ttest_ind(x, y, equal_var=False)
    print(f"{etq:<14}{len(x):>5}{x.mean():>9.1f}{y.mean():>8.1f}"
          f"{x.mean()-y.mean():>8.1f}{x.std():>10.1f}{t:>7.2f}{p:>8.3f}")

print()
print("  contraste con el contado de Yahoo (mismo periodo aprox):")
print("     contado 2012-2026 : +18 a +32 bp segun tramo, t=2,75 a 2,99")

# ============================================================ 2. el perfil
print()
print("=" * 88)
print("2. ¿DONDE DENTRO DE LA NOCHE?  bp acumulados desde el cierre de 16:00")
print("=" * 88)
NOMS = [n for _, n in HITOS] + [n for _, n in HITOS_D]
print(f"{'':<12}" + "".join(f"{n:>8}" for n in NOMS))
print("-" * 88)
for lab, sel in [("FOMC", d["es_fomc"]), ("resto", ~d["es_fomc"])]:
    print(f"{lab:<12}" + "".join(
        f"{d.loc[sel, 'c_' + n].mean():>8.1f}" for n in NOMS))
print(f"{'diferencia':<12}" + "".join(
    f"{d.loc[d['es_fomc'], 'c_' + n].mean() - d.loc[~d['es_fomc'], 'c_' + n].mean():>8.1f}"
    for n in NOMS))

# ============================================== 3. ventanas mas cortas
print()
print("=" * 88)
print("3. ¿SE PUEDE AGUANTAR MENOS TIEMPO?  ventanas que acaban en 09:30")
print("=" * 88)
print(f"{'desde':>8}{'horas':>7}{'n':>5}{'dif bruta':>11}{'t':>7}"
      f"{'swap':>7}{'spread':>8}{'NETO':>8}")
print("-" * 88)
INICIOS = [("16:00", CIERRE, 17.5), ("19:00", 19 * 60, 14.5),
           ("23:00", 23 * 60, 10.5), ("01:00", 1 * 60, 8.5),
           ("05:00", 5 * 60, 4.5), ("07:00", 7 * 60, 2.5),
           ("08:30", 8 * 60 + 30, 1.0)]
SP = 1.5          # spread de ida en bp
for nom, mm, horas in INICIOS:
    col = "c_" + nom
    if col not in d.columns:
        continue
    # retorno desde 'nom' hasta 09:30  =  acumulado(09:30) - acumulado(nom)
    r = d["c_09:30"] - d[col]
    x, y = r[d["es_fomc"]].dropna(), r[~d["es_fomc"]].dropna()
    if len(x) < 20:
        continue
    t, _ = stats.ttest_ind(x, y, equal_var=False)
    dif = x.mean() - y.mean()
    swap = horas * SWAP_HORA
    neto = dif - swap - 2 * SP
    print(f"{nom:>8}{horas:>7.1f}{len(x):>5}{dif:>11.1f}{t:>7.2f}"
          f"{-swap:>7.2f}{-2*SP:>8.1f}{neto:>8.1f}")

# ============================================== 4. economia final
print()
print("=" * 88)
print("4. ECONOMIA DE LA MEJOR VENTANA")
print("=" * 88)
mejor = None
for nom, mm, horas in INICIOS:
    col = "c_" + nom
    if col not in d.columns:
        continue
    r = d["c_09:30"] - d[col]
    x = r[d["es_fomc"]].dropna()
    y = r[~d["es_fomc"]].dropna()
    if len(x) < 20:
        continue
    for sp in (0.75, 1.5, 2.5):
        neto = x - horas * SWAP_HORA - 2 * sp
        if neto.std() == 0:
            continue
        sh = neto.mean() / neto.std() * np.sqrt(8)      # 8 eventos al año
        if mejor is None or sh > mejor[0]:
            mejor = (sh, nom, horas, sp, neto.mean(), neto.std(), len(x))
sh, nom, horas, sp, mn, sd, n = mejor
print("  ventana optima: desde las %s hasta 09:30 ET  (%.1f horas)" % (nom, horas))
print("  spread asumido: %.2f bp de ida" % sp)
print("  neto por evento: %+.1f bp   (sd %.1f, n=%d)" % (mn, sd, n))
print("  8 eventos al año -> %+.0f bp/año  ·  Sharpe anual %.2f" % (mn * 8, sh))
print()
print("  Con vol anual implicita de %.2f%%, y optimo de 6%% para instant"
      % (sd * np.sqrt(8) / 100))
print("  funding, el apalancamiento necesario seria x%.1f"
      % (6.0 / max(1e-9, sd * np.sqrt(8) / 100)))
