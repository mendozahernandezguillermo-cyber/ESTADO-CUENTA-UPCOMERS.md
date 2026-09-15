#!/usr/bin/env python3
"""
EL FACTOR DEL GUARDIAN SE APLICA AL ABRIR, NO CADA DIA. ¿CUANTO CAMBIA ESO?

Mis simulaciones aplicaban el factor de tamaño A LOS RETORNOS DE CADA DIA:

    f = recorte((equity - suelo) / 25000 / 0.05, 0.25, 1)
    eq = ini + ini * retorno_del_dia * f          # f, todos los dias

Eso describe un sistema que encoge la exposicion el MISMO dia en que el margen
se estrecha. El sistema real no puede: las posiciones se dimensionan al abrir
y mantienen su tamaño hasta el siguiente rebalanceo, hasta 21 sesiones despues.

DONDE ESTA Y DONDE NO ESTA EL ERROR
  · Pata #1 (pre-FOMC): CORRECTA. Su retorno solo es distinto de cero los dias
    de evento, y el EA lee el factor justo antes de abrir. Aplicar f ese mismo
    dia es exactamente lo que hace el codigo.
  · Pata #2 (trend): MAL. Su retorno es distinto de cero todos los dias, pero
    el tamaño se fija una vez al mes.

Se comparan cinco variantes:
  A  factor diario          lo que simule (optimista)
  B  factor mensual         el sistema REAL
  C  sin factor             referencia sin control
  D  mensual + redimensiona si el factor cambia mas del 20%
  E  mensual + redimensiona si cambia mas del 10%

El coste de redimensionar se cobra: cruzar el spread de las 7 posiciones con
los spreads REALES medidos en el terminal sale a 0,59 bp de la equity.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260904)
BLOQUE, SUB = 5, 8
N, DIAS = 20_000, 504
CUENTA, DD, DD_DIA = 25_000.0, 0.07, 0.04
UMBRAL, MIN_DIAS, MIN_BEN, BEST = 250.0, 6, 0.005, 0.20
REF, FMIN = 0.05, 0.25
DIAS_REBAL = 21               # sesiones entre rebalanceos
COSTE_REDIM_BP = 0.59         # bp de equity por redimensionar la cesta


def cargar(vol=0.045, w2=0.30):
    A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
    s1 = np.clip(A["s1"].values, -0.008, 0.008)
    s2 = A["s2"].values
    cart = (1 - w2) * s1 + w2 * s2
    lev = vol / (cart.std() * np.sqrt(252))
    return (1 - w2) * s1 * lev, w2 * s2 * lev


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


def simular(g1, g2, sd, modo, umbral_redim=None):
    """modo: 'diario' | 'mensual' | 'sin'"""
    n, dias = g1.shape
    bal = np.full(n, CUENTA); hwm = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - DD))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    extra = np.zeros(n); npag = np.zeros(n, int)
    f_trend = np.ones(n)          # tamaño con el que se abrio la cesta
    n_redim = np.zeros(n, int)
    brecha = []                   # |f_ahora - f_trend| medio
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break
        ini = bal.copy()
        pdd = ini * (1 - DD_DIA)
        pdia = np.maximum(piso, pdd)

        if modo == "sin":
            f_ahora = np.ones(n)
        else:
            f_ahora = np.clip((ini - piso) / CUENTA / REF, FMIN, 1.0)

        # ---- tamaño con el que opera HOY la pata #2
        if modo == "diario":
            f2 = f_ahora
        elif modo == "sin":
            f2 = np.ones(n)
        else:
            if d % DIAS_REBAL == 0:
                f_trend = f_ahora.copy()
            elif umbral_redim is not None:
                # redimensiona si el factor se ha desviado lo suficiente
                dif = np.abs(f_ahora - f_trend) / np.maximum(f_trend, 1e-9)
                hay = vivo & (dif > umbral_redim)
                if hay.any():
                    f_trend = np.where(hay, f_ahora, f_trend)
                    n_redim += hay
                    bal = bal - np.where(hay, bal * COSTE_REDIM_BP / 1e4, 0.0)
                    ini = bal.copy()
            f2 = f_trend
        brecha.append(np.abs(f_ahora - f2)[vivo].mean() if vivo.any() else 0.0)

        # ---- 1. el hueco de la #1: SIEMPRE con el factor del momento,
        #         porque el EA lo lee justo antes de abrir
        eq = ini + ini * g1[:, d] * f_ahora
        vivo = vivo & ~(vivo & (eq < pdia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        # ---- 2. la sesion de la #2: con el tamaño con que se abrio
        act = np.where(vivo)[0]
        eqf = eq.copy()
        if act.size:
            fa = f2[act]
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

        prof = bal - CUENTA
        pide = vivo & (prof >= UMBRAL) & (cual >= MIN_DIAS) \
               & (mejor <= BEST * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag += pide
            bal = np.where(pide, CUENTA, bal)
            hwm = np.where(pide, CUENTA, hwm)
            piso = np.where(pide, CUENTA * (1 - DD), piso)
            lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    return dict(neto=extra * 0.90 - 50.0, npag=npag, quemada=~vivo,
                n_redim=n_redim, brecha=float(np.mean(brecha)))


h1, h2 = cargar()
g1, g2 = bootstrap_par(h1, h2, DIAS, N)
sd = h2.std()

E = "=" * 88
print(E)
print("EL FACTOR: DIARIO CONTRA MENSUAL   ·   25K, DD 7%, 2 años, 20.000 caminos")
print(E)
casos = [
    ("A  factor DIARIO (lo que simule)", "diario", None),
    ("B  factor MENSUAL (el sistema real)", "mensual", None),
    ("C  sin factor (referencia)", "sin", None),
    ("D  mensual + redim. si cambia >20%", "mensual", 0.20),
    ("E  mensual + redim. si cambia >10%", "mensual", 0.10),
]
print(f"  {'variante':<38}{'P(quema)':>10}{'P(cobro)':>10}"
      f"{'EV anual':>11}{'redim/año':>11}{'brecha f':>10}")
print("  " + "-" * 88)
res = {}
for nom, modo, ur in casos:
    r = simular(g1, g2, sd, modo, ur)
    res[nom] = r
    print(f"  {nom:<38}{r['quemada'].mean():>9.1%}"
          f"{(r['npag'] > 0).mean():>10.1%}{r['neto'].mean()/2:>10,.0f}$"
          f"{r['n_redim'].mean()/2:>11.1f}{r['brecha']:>10.3f}")

a = res["A  factor DIARIO (lo que simule)"]
b = res["B  factor MENSUAL (el sistema real)"]
c = res["C  sin factor (referencia)"]
print()
print("  LO QUE IMPORTA:")
print(f"    lo que te dije      (A) : quema {a['quemada'].mean():.1%}")
print(f"    lo que tienes       (B) : quema {b['quemada'].mean():.1%}"
      f"   <- {b['quemada'].mean()/max(a['quemada'].mean(),1e-9):.1f}x mas")
print(f"    sin ningun control  (C) : quema {c['quemada'].mean():.1%}")
prot = 1 - (b['quemada'].mean() - a['quemada'].mean()) / \
           max(c['quemada'].mean() - a['quemada'].mean(), 1e-9)
print(f"\n    el factor mensual conserva el {prot:.0%} de la proteccion que"
      f" prometia el diario")

print()
print(E)
print("¿MERECE LA PENA REDIMENSIONAR ENTRE REBALANCEOS?")
print(E)
for nom in ("B  factor MENSUAL (el sistema real)",
            "D  mensual + redim. si cambia >20%",
            "E  mensual + redim. si cambia >10%"):
    r = res[nom]
    print(f"  {nom:<38} quema {r['quemada'].mean():>5.1%}"
          f"  cobro {(r['npag']>0).mean():>5.1%}"
          f"  EV {r['neto'].mean()/2:>7,.0f}$"
          f"  redim {r['n_redim'].mean()/2:>5.1f}/año")
print()
print("  'brecha f' es la diferencia media entre el factor que tocaria hoy y el")
print("  que lleva puesta la cesta. Cuanto mayor, mas desalineada esta.")
