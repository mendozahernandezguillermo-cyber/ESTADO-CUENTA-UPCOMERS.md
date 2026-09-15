#!/usr/bin/env python3
"""
RECONSTRUCCION DEL MODELO DE COBROS CON LAS REGLAS REALES DE UPCOMERS.

Mi modelo anterior tenia CUATRO supuestos falsos, todos en la direccion
optimista. Documentacion de la firma (Payout Structure CFD + Best Day Rule):

  1. HAY UN TOPE POR COBRO, escalonado. En 25K: 250, 500, 750, 1.000, 1.250,
     1.560, 1.875 y a partir del 8º sin tope. Yo retiraba TODO el beneficio.
  2. LA CUENTA NO SE REINICIA. Yo devolvia saldo, pico y suelo al inicial.
     Solo baja el importe retirado. Tras el 7º cobro si se reinicia.
  3. EL BENEFICIO POR ENCIMA DEL TOPE QUEDA ATRAPADO PARA SIEMPRE. Sigue en el
     saldo y cuenta para el drawdown, pero no es retirable en ningun segmento
     futuro. Cada cobro se calcula solo sobre el beneficio del segmento en
     curso, o sea desde el cobro anterior.
  4. COMISIONES DE PROCESO: 19,9 $ + 2,49% por transferencia. Yo no cobraba
     ninguna.

Y un efecto de segundo orden que nadie diseñó y que sale de la combinacion:
el beneficio atrapado NO es retirable pero SI cuenta para la equity, asi que
actua como colchon contra el suelo del trailing. Se mide.

La regla del mejor dia con su formula exacta: dia% = P&L neto del dia dividido
por el P&L neto TOTAL del ciclo. Los dias en perdida bajan el denominador y
empeoran el ratio. Dias en UTC.
"""
import os, glob, csv, re
import datetime as dt
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260905)
BLOQUE, SUB = 5, 8
N = 20_000
CUENTA = 25_000.0
DD, DD_DIA = 0.07, 0.04
SPLIT = 0.90                  # a confirmar en el panel
MIN_DIAS, MIN_BEN, BEST = 6, 0.005, 0.20
MIN_SEGMENTO = 0.01 * CUENTA  # el 1% de beneficio total
REF, FMIN = 0.05, 0.25
DIAS_REBAL = 21
CUOTA = 50.0
FEE_FIJA, FEE_PCT = 19.9, 0.0249
TOPES = [250., 500., 750., 1000., 1250., 1560., 1875.]   # 8º+ sin tope
STOP_BP = 80.0

# =================================================== serie de la #1 desde M1
DIR = "../nas100-data/raw"
MIN_ANTES, VENTANA = 3, 45


def es_verano(u):
    a = u.year
    d = (dt.date(a, 3, 1).weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    d = (dt.date(a, 11, 1).weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano(u) else 5))


FECHAS = sorted(set(re.findall(
    r"\b(20\d{6})\b",
    open("../mql5/fechas_fomc_completas.txt", encoding="utf-8").read())))
interes = set()
for f in FECHAS:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

print("leyendo M1 ...")
barras = {}
for path in sorted(glob.glob(os.path.join(DIR, "usatechidxusd-m1-*.csv"))):
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            try:
                ms = int(row[0]); o = float(row[1]); h = float(row[2])
                l = float(row[3]); c = float(row[4])
            except (ValueError, IndexError):
                continue
            if c <= 0:
                continue
            ny = utc_a_ny(dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms))
            if ny.date() in interes:
                barras.setdefault(ny.date(), []).append((ny, o, h, l, c))
for k in barras:
    barras[k].sort()

EVENTOS = []
for f in FECHAS:
    anuncio = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    if anuncio not in barras:
        continue
    ent = None
    for k in range(1, 5):
        cand = anuncio - dt.timedelta(days=k)
        if cand.weekday() < 5:
            ent = cand
            break
    if ent is None or ent not in barras:
        continue
    e = None
    for b in barras[ent]:
        m = b[0].hour * 60 + b[0].minute
        if 16 * 60 - MIN_ANTES <= m <= 16 * 60 + VENTANA:
            e = b
            break
    if e is None:
        continue
    seq = [b for b in barras[ent] if b[0] > e[0]] + \
          [b for b in barras[anuncio]
           if (b[0].hour * 60 + b[0].minute) <= 9 * 60 + 30]
    if seq:
        EVENTOS.append((anuncio, e[4], seq))
print(f"eventos M1: {len(EVENTOS)}")


def serie_s1(tp_bp):
    out = {}
    for anuncio, p_ent, seq in EVENTOS:
        sl = p_ent * (1 - STOP_BP / 1e4)
        tp = p_ent * (1 + tp_bp / 1e4)
        sal = None
        for (t, o, h, l, c) in seq:
            if l <= sl:
                sal = o if o <= sl else sl
                break
            if h >= tp:
                sal = tp
                break
        if sal is None:
            sal = seq[-1][4]
        out[pd.Timestamp(anuncio)] = sal / p_ent - 1.0
    return out


A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
s2_full = A["s2"]


def preparar(tp_bp, w2=0.30, vol=0.045):
    s1 = pd.Series(0.0, index=s2_full.index)
    for ts, r in serie_s1(tp_bp).items():
        if ts in s1.index:
            s1.loc[ts] = r
    D = pd.DataFrame({"s1": s1, "s2": s2_full}).dropna()
    D = D[D.index >= "2011-01-01"]
    cart = (1 - w2) * D["s1"] + w2 * D["s2"]
    lev = vol / (cart.std() * np.sqrt(252))
    riesgo = (1 - w2) * lev * STOP_BP / 100.0
    return (((1 - w2) * D["s1"] * lev).values,
            (w2 * D["s2"] * lev).values, riesgo)


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


# =================================================== simulacion de la cuenta
def simular(g1, g2, sd, modelo="real"):
    """modelo: 'real' (topes, sin reinicio, atrapado, comisiones)
               'viejo' (lo que simulaba antes)"""
    n, dias = g1.shape
    bal = np.full(n, CUENTA); hwm = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - DD))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    ref_seg = np.full(n, CUENTA)          # saldo al inicio del segmento
    recibido = np.zeros(n)                # neto de comisiones, en el bolsillo
    atrapado = np.zeros(n)                # beneficio que ya no se puede sacar
    npag = np.zeros(n, int)
    d1 = np.full(n, -1)
    f_trend = np.ones(n)
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break
        ini = bal.copy()
        pdd = ini * (1 - DD_DIA)
        pdia = np.maximum(piso, pdd)
        f_now = np.clip((ini - piso) / CUENTA / REF, FMIN, 1.0)
        if d % DIAS_REBAL == 0:
            f_trend = f_now.copy()

        eq = ini + ini * g1[:, d] * f_now
        vivo = vivo & ~(vivo & (eq < pdia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        act = np.where(vivo)[0]
        eqf = eq.copy()
        if act.size:
            fa = f_trend[act]
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

        seg = bal - ref_seg               # beneficio DEL SEGMENTO
        pide = (vivo & (seg >= MIN_SEGMENTO) & (cual >= MIN_DIAS)
                & (mejor <= BEST * np.maximum(seg, 1e-9)))
        if not pide.any():
            continue

        idx = np.where(pide)[0]
        if modelo == "viejo":
            recibido[idx] += seg[idx] * SPLIT
            bal[idx] = CUENTA
            hwm[idx] = CUENTA
            piso[idx] = CUENTA * (1 - DD)
            lock[idx] = False
            ref_seg[idx] = CUENTA
        else:
            tope = np.array([TOPES[min(npag[i], len(TOPES) - 1)]
                             if npag[i] < len(TOPES) else 1e12 for i in idx])
            cuota_trader = seg[idx] * SPLIT
            bruto = np.minimum(cuota_trader, tope)
            neto = np.maximum(bruto - FEE_FIJA - bruto * FEE_PCT, 0.0)
            recibido[idx] += neto
            sacado = bruto / SPLIT                     # sale del saldo
            atrapado[idx] += np.maximum(seg[idx] - sacado, 0.0)
            bal[idx] -= sacado
            ref_seg[idx] = bal[idx]                    # nuevo segmento
        d1[idx] = np.where(d1[idx] < 0, d, d1[idx])
        npag[idx] += 1
        cual[idx] = 0
        mejor[idx] = 0.0

        # tras el 7º cobro la cuenta se reinicia y queda sin tope
        if modelo != "viejo":
            res = idx[npag[idx] == len(TOPES)]
            if res.size:
                bal[res] = CUENTA; hwm[res] = CUENTA
                piso[res] = CUENTA * (1 - DD); lock[res] = False
                ref_seg[res] = CUENTA

    return dict(neto=recibido - CUOTA, npag=npag, quemada=~vivo,
                atrapado=atrapado, d1=d1, bal=bal, recibido=recibido)


E = "=" * 92
a1, a2, riesgo = preparar(50.0)
print(f"configuracion: TP 50 bp · stop 80 bp · riesgo {riesgo:.2f}% · w2 30%")

print()
print(E)
print("EL TAMAÑO DEL ERROR: modelo viejo contra modelo real")
print(E)
print(f"  {'horizonte':<12}{'modelo':<10}{'P(cobro)':>10}{'cobros':>8}"
      f"{'EV anual':>11}{'mediana':>11}{'atrapado':>11}{'P(quema)':>10}")
print("  " + "-" * 84)
guard = {}
for anios in (2, 3, 5):
    g1, g2 = bootstrap_par(a1, a2, int(252 * anios), N)
    for modelo in ("viejo", "real"):
        r = simular(g1, g2, a2.std(), modelo)
        guard[(anios, modelo)] = r
        print(f"  {(str(anios)+' años') if modelo=='viejo' else '':<12}"
              f"{modelo:<10}{(r['npag']>0).mean():>10.1%}{r['npag'].mean():>8.2f}"
              f"{r['neto'].mean()/anios:>10,.0f}${np.median(r['neto']):>10,.0f}$"
              f"{r['atrapado'].mean():>10,.0f}${r['quemada'].mean():>10.1%}")
    print()

v2, r2 = guard[(2, "viejo")], guard[(2, "real")]
print(f"  A dos años: el EV pasa de {v2['neto'].mean()/2:,.0f} $/año a "
      f"{r2['neto'].mean()/2:,.0f} $/año  "
      f"({r2['neto'].mean()/max(v2['neto'].mean(),1e-9):.2f}x)")

# ------------------------------------------------ reoptimizar el take profit
print()
print(E)
print("REOPTIMIZAR EL TAKE PROFIT CON EL BENEFICIO ATRAPADO DENTRO")
print(E)
print(f"  {'TP':>6}{'riesgo':>9}{'P(cobro)':>10}{'1er cobro':>11}"
      f"{'EV anual':>11}{'atrapado':>11}{'recibido/atrapado':>19}")
print("  " + "-" * 78)
for tp in (30.0, 40.0, 50.0, 60.0, 80.0):
    b1, b2, rg = preparar(tp)
    g1, g2 = bootstrap_par(b1, b2, 504, N)
    r = simular(g1, g2, b2.std(), "real")
    dd = r['d1'][r['d1'] >= 0]
    ratio = r['recibido'].mean() / max(r['atrapado'].mean(), 1e-9)
    print(f"  {tp:>5.0f}{rg:>8.2f}%{(r['npag']>0).mean():>10.1%}"
          f"{(np.median(dd) if len(dd) else np.nan):>10.0f}d"
          f"{r['neto'].mean()/2:>10,.0f}${r['atrapado'].mean():>10,.0f}$"
          f"{ratio:>19.2f}")

# ------------------------------------------------ el colchon del atrapado
print()
print(E)
print("EFECTO COLATERAL: el beneficio atrapado protege contra el suelo")
print(E)
r5 = guard[(5, "real")]
vivos = r5['npag'] > 0
print("  El beneficio atrapado no es retirable, pero sigue en la equity y")
print("  aleja el saldo del suelo del trailing. Sobre 5 años:")
print(f"     atrapado medio                 : {r5['atrapado'].mean():>9,.0f} $")
print(f"     saldo final medio              : {r5['bal'].mean():>9,.0f} $")
print(f"     P(quema) con al menos un cobro : "
      f"{r5['quemada'][vivos].mean():>9.1%}")
print(f"     P(quema) sin ningun cobro      : "
      f"{r5['quemada'][~vivos].mean():>9.1%}")
