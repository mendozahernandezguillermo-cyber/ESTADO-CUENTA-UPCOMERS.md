#!/usr/bin/env python3
"""
¿CONVIENE UN TAKE PROFIT ASIMETRICO?

La regla de consistencia de Upcomers mira el MEJOR DIA y exige que no pase del
20% del beneficio total. Medido: el 99,9% de los caminos que no cobran estan
bloqueados por esa regla, y el mejor dia coincide con el take profit de la #1
(333 $ medidos contra 337,50 $ teoricos).

El stop y el TP los puse SIMETRICOS en 80 bp. Pero la regla no mira el stop.
Asi que el TP es una palanca directa sobre la probabilidad de cobro y nunca la
he barrido por separado.

POR QUE SE MIDE SOBRE M1 Y NO TRUNCANDO LA SERIE DIARIA
Un TP se toca INTRADIA. Recortar el retorno de cierre del dia solo captura los
eventos que CIERRAN por encima del TP, y subestima muchisimo su efecto: un
evento que acaba en +20 bp pero que paso por +50 bp habria cerrado en el TP.
Con los M1 se recorre barra a barra y se ve el toque de verdad.

SUPUESTO CONSERVADOR: si en el mismo minuto se tocan stop y TP, se asume STOP.
Con un TP mas corto eso ocurre mas veces, asi que el sesgo va en contra del TP
corto. Es el lado seguro.
"""
import os
import glob
import csv
import re
import datetime as dt
import numpy as np
import pandas as pd

DIR = "../nas100-data/raw"
STOP_BP = 80.0
MIN_ANTES, VENTANA_MIN = 3, 45
TPS = [30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 1e9]


def es_verano(u):
    a = u.year
    d = (dt.date(a, 3, 1).weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    d = (dt.date(a, 11, 1).weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano(u) else 5))


FECHAS = sorted(set(re.findall(r"\b(20\d{6})\b",
                open("fechas_fomc_completas.txt", encoding="utf-8").read())))
interes = set()
for f in FECHAS:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

print("leyendo M1 de Dukascopy ...")
barras = {}
for path in sorted(glob.glob(os.path.join(DIR, "usatechidxusd-m1-*.csv"))):
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            try:
                ms = int(row[0])
            except (ValueError, IndexError):
                continue
            ny = utc_a_ny(dt.datetime(1970, 1, 1) +
                          dt.timedelta(milliseconds=ms))
            if ny.date() not in interes:
                continue
            try:
                o, h, l, c = (float(row[1]), float(row[2]),
                              float(row[3]), float(row[4]))
            except (ValueError, IndexError):
                continue
            if c > 0:
                barras.setdefault(ny.date(), []).append((ny, o, h, l, c))
for k in barras:
    barras[k].sort()

# ---- secuencias precalculadas por evento (entrada y camino hasta la salida)
EVENTOS = []
for f in FECHAS:
    anuncio = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    if anuncio not in barras:
        continue
    ent_dia = None
    for k in range(1, 5):
        cand = anuncio - dt.timedelta(days=k)
        if cand.weekday() < 5:
            ent_dia = cand
            break
    if ent_dia is None or ent_dia not in barras:
        continue
    ini_m, fin_m = 16 * 60 - MIN_ANTES, 16 * 60 + VENTANA_MIN
    ent = None
    for b in barras[ent_dia]:
        m = b[0].hour * 60 + b[0].minute
        if ini_m <= m <= fin_m:
            ent = b
            break
    if ent is None:
        continue
    seq = [b for b in barras[ent_dia] if b[0] > ent[0]] + \
          [b for b in barras[anuncio]
           if (b[0].hour * 60 + b[0].minute) <= 9 * 60 + 30]
    if seq:
        EVENTOS.append((anuncio, ent[4], seq))

print(f"eventos con datos M1: {len(EVENTOS)}")


def simular_tp(tp_bp):
    """Recorre los M1 con stop 80 bp y take profit tp_bp."""
    res = []
    for anuncio, p_ent, seq in EVENTOS:
        sl = p_ent * (1 - STOP_BP / 10000.0)
        tp = p_ent * (1 + tp_bp / 10000.0)
        salida, motivo = None, ""
        for (t, o, h, l, c) in seq:
            if l <= sl:                       # el stop manda si coinciden
                salida = o if o <= sl else sl
                motivo = "stop"
                break
            if h >= tp:
                salida, motivo = tp, "tp"
                break
        if salida is None:
            salida, motivo = seq[-1][4], "hora"
        res.append((anuncio, (salida / p_ent - 1.0), motivo))
    return res


# ---------------------------------------------------- serie diaria de la #2
A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
s2_full = A["s2"]

RNG = np.random.default_rng(20260903)
BLOQUE, SUB, N = 5, 8, 15_000
CUENTA, DD, DD_DIA = 25_000.0, 0.07, 0.04
UMBRAL, MIN_DIAS, MIN_BEN, BEST = 250.0, 6, 0.005, 0.20
REF, FMIN, W2 = 0.05, 0.25, 0.30


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


def cuenta_sim(g1, g2, sd):
    n, dias = g1.shape
    bal = np.full(n, CUENTA); hwm = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - DD))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    extra = np.zeros(n); npag = np.zeros(n, int)
    d1 = np.full(n, -1); mejor_hist = np.zeros(n)
    paso0 = sd / np.sqrt(SUB)
    for d in range(dias):
        if not vivo.any():
            break
        ini = bal.copy()
        pdd = ini * (1 - DD_DIA)
        pdia = np.maximum(piso, pdd)
        f = np.clip((ini - piso) / CUENTA / REF, FMIN, 1.0)
        eq = ini + ini * g1[:, d] * f
        vivo = vivo & ~(vivo & (eq < pdia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)
        act = np.where(vivo)[0]
        eqf = eq.copy()
        if act.size:
            fa = f[act]
            b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
            k = np.arange(1, SUB + 1) / SUB
            br = (b - k[None, :] * b[:, -1:]) * fa[:, None] \
                 + k[None, :] * (g2[act, d] * fa)[:, None]
            cam = eq[act][:, None] + ini[act][:, None] * br
            pico = np.maximum.accumulate(np.maximum(cam, hwm[act][:, None]), 1)
            pa = np.where(lock[act][:, None],
                          np.maximum(piso[act][:, None], CUENTA),
                          np.maximum(piso[act][:, None], pico * (1 - DD)))
            pa = np.maximum(pa, pdd[act][:, None])
            vivo[act] = ~(cam < pa).any(1)
            eqf[act] = cam[:, -1]
            hwm[act] = np.maximum(hwm[act], pico[:, -1])
        vivo = vivo & ~(vivo & (eqf < pdia))
        pnl = eqf - ini
        bal = np.where(vivo, eqf, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm * (1 - DD) >= CUENTA))
        piso = np.where(vivo & lock, np.maximum(piso, CUENTA),
                        np.where(vivo, np.maximum(piso, hwm * (1 - DD)), piso))
        cual = cual + (vivo & (pnl >= MIN_BEN * CUENTA))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        mejor_hist = np.maximum(mejor_hist, np.where(vivo, pnl, 0.0))
        prof = bal - CUENTA
        pide = vivo & (prof >= UMBRAL) & (cual >= MIN_DIAS) \
               & (mejor <= BEST * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag += pide
            d1 = np.where(pide & (d1 < 0), d, d1)
            bal = np.where(pide, CUENTA, bal)
            hwm = np.where(pide, CUENTA, hwm)
            piso = np.where(pide, CUENTA * (1 - DD), piso)
            lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)
    return dict(neto=extra * 0.90 - 50.0, npag=npag, quemada=~vivo,
                d1=d1, mejor=mejor_hist)


E = "=" * 96
print()
print(E)
print("PARTE 1: EL EFECTO DEL TAKE PROFIT SOBRE LA #1  (M1 reales, stop fijo en 80 bp)")
print(E)
print(f"  {'TP':>7}{'media bp':>11}{'t':>7}{'% pos':>8}"
      f"{'salidas: hora / tp / stop':>28}{'peor evento':>13}")
print("  " + "-" * 74)
resultados = {}
for tp in TPS:
    r = simular_tp(tp)
    rs = np.array([x[1] for x in r]) * 10000.0
    mot = pd.Series([x[2] for x in r]).value_counts()
    t = rs.mean() / rs.std(ddof=1) * np.sqrt(len(rs))
    resultados[tp] = r
    etq = "sin TP" if tp > 1e8 else f"{tp:.0f}"
    print(f"  {etq:>7}{rs.mean():>+10.2f}{t:>7.2f}{(rs > 0).mean():>8.1%}"
          f"{mot.get('hora',0):>12}{mot.get('tp',0):>7}{mot.get('stop',0):>8}"
          f"{rs.min():>13.1f}")

print()
print(E)
print("PARTE 2: LO QUE LE HACE A LA CUENTA")
print(E)
fechas_s2 = s2_full.index
print(f"  {'TP':>7}{'riesgo':>9}{'apalanc':>9}{'mejor dia':>11}"
      f"{'liston 20%':>12}{'P(cobro)':>10}{'1er cobro':>11}"
      f"{'P(quema)':>10}{'EV anual':>11}")
print("  " + "-" * 90)
mejor_cfg = None
for tp in TPS:
    # serie diaria de la #1 con este TP, alineada con la #2
    s1 = pd.Series(0.0, index=fechas_s2)
    for anuncio, ret, motivo in resultados[tp]:
        ts = pd.Timestamp(anuncio)
        if ts in s1.index:
            s1.loc[ts] = ret
    D = pd.DataFrame({"s1": s1, "s2": s2_full}).dropna()
    D = D[D.index >= "2011-01-01"]          # rango con datos M1
    cart = (1 - W2) * D["s1"] + W2 * D["s2"]
    lev = 0.045 / (cart.std() * np.sqrt(252))
    riesgo = (1 - W2) * lev * STOP_BP / 100.0
    a1 = ((1 - W2) * D["s1"] * lev).values
    a2 = (W2 * D["s2"] * lev).values
    g1, g2 = bootstrap_par(a1, a2, 504, N)
    r = cuenta_sim(g1, g2, a2.std())
    dd1 = r['d1'][r['d1'] >= 0]
    md = r['mejor'].mean()
    etq = "sin TP" if tp > 1e8 else f"{tp:.0f}"
    pc = (r['npag'] > 0).mean()
    print(f"  {etq:>7}{riesgo:>8.2f}%{lev*(1-W2):>9.3f}{md:>10.0f}$"
          f"{md*5:>11.0f}${pc:>10.1%}"
          f"{(np.median(dd1) if len(dd1) else np.nan):>10.0f}d"
          f"{r['quemada'].mean():>10.1%}{r['neto'].mean()/2:>10,.0f}$")
    if mejor_cfg is None or pc > mejor_cfg[1]:
        mejor_cfg = (tp, pc, riesgo, r['neto'].mean()/2)

print()
print(f"  Maximo de P(cobro): TP = {mejor_cfg[0]:.0f} bp  ->  {mejor_cfg[1]:.1%}"
      f"  con riesgo {mejor_cfg[2]:.2f}%  y EV {mejor_cfg[3]:,.0f} $/año")
print()
print("  Nota: el 'riesgo' cambia con el TP porque un TP distinto altera la")
print("  volatilidad de la pata, y el apalancamiento se recalcula para que la")
print("  cartera siga en 4,5%. Es el InpRiesgoPorEvento que habria que poner.")
