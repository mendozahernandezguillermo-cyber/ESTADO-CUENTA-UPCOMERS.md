#!/usr/bin/env python3
"""
LAS REGLAS DE UPCOMERS, VERIFICADAS CONTRA SU PANEL

Hasta ahora simulaba con mi lectura del reglamento. El panel de una cuenta
real de 25K la ha corregido en tres puntos:

  1. El limite DIARIO es un 4% RELATIVO a la equity de inicio del dia,
     no un 4% del saldo inicial.
         panel  23.769,38  =  24.759,77 x 0,96   (error 0,0008)
         mi version absoluta daria 23.759,77, casi 10 $ mas abajo.

  2. El limite GENERAL es un % RELATIVO a la marca de agua alta.
         panel  23.752,95  =  25.003,10 x 0,95   (error 0,005)
     La forma (trailing sobre el pico de equity) ya la tenia bien; el
     denominador, no.

  3. Los dias minimos de trading son 5, no 6.

Y confirma dos cosas que estaban en el aire:

  4. La regla de consistencia del mejor dia es del 20% TAMBIEN en el
     producto CFD. Era la incognita que valia ~1.400 $ por cuenta.
  5. El drawdown se mide contra el pico, en tiempo real, incluyendo el
     P/G flotante (el panel tiene campo propio para el flotante).

Este script mide si esas correcciones cambian el plan. Las dos primeras van
a favor: un limite relativo se ENSANCHA cuando la cuenta crece.
"""
import numpy as np
import pandas as pd

RNG    = np.random.default_rng(20260829)
BLOQUE = 5
SUB    = 8
CUOTA  = 90.0
SPLIT  = 0.90
UMBRAL = 1_000.0
MINBEN = 0.005
BESTDAY= 0.20
DIAS   = 504
N      = 20_000
COSTE  = 3.5


def cargar(vol_objetivo=0.045, trunc=0.008):
    A = pd.read_csv("../planes/salida/cartera_diaria.csv",
                    index_col=0, parse_dates=True)
    s2 = A["s2"].values
    iv1, iv2 = 1 / A["s1"].values.std(), 1 / s2.std()
    w1 = iv1 / (iv1 + iv2)
    w2 = 1 - w1
    s1 = np.clip(A["s1"].values, -trunc, trunc)
    cart = w1 * s1 + w2 * s2
    lev = vol_objetivo / (cart.std() * np.sqrt(252))
    return w1 * s1 * lev, w2 * s2 * lev, w1, w2, lev


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb  = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


def simular(g1, g2, sd_sesion, cuenta=50_000.0, dd=0.07, dd_dia=0.04,
            relativo=True, min_dias=5, escala_ref=0.0, escala_min=0.25,
            colchon=0.0, coste_bp=COSTE, best_day=BESTDAY, cuota=CUOTA,
            umbral=UMBRAL, lock=True):
    n, dias = g1.shape

    bal   = np.full(n, cuenta)
    hwm   = np.full(n, cuenta)
    piso  = np.full(n, cuenta * (1 - dd))
    locked= np.zeros(n, bool)
    vivo  = np.ones(n, bool)
    cual  = np.zeros(n, int)
    mejor = np.zeros(n)
    extra = np.zeros(n)
    npag  = np.zeros(n, int)
    ndisp = np.zeros(n, int)
    fsum  = np.zeros(n)
    fdias = np.zeros(n, int)

    col_t = colchon * cuenta
    paso0 = sd_sesion / np.sqrt(SUB)

    def piso_dia_de(ini):
        return (ini * (1 - dd_dia) if relativo else ini - dd_dia * cuenta)

    def piso_tr_de(pico):
        return (pico * (1 - dd) if relativo else pico - dd * cuenta)

    for d in range(dias):
        if not vivo.any():
            break

        ini_dia  = bal.copy()
        pd_dia   = piso_dia_de(ini_dia)
        piso_dia = np.maximum(piso, pd_dia)

        if escala_ref > 0.0:
            margen = (ini_dia - piso) / cuenta
            f = np.clip(margen / escala_ref, escala_min, 1.0)
        else:
            f = np.ones(n)
        fsum  += np.where(vivo, f, 0.0)
        fdias += vivo

        # ---- 1. el hueco de la #1 llega de golpe
        eq = ini_dia + ini_dia * g1[:, d] * f
        vivo = vivo & ~(vivo & (eq < piso_dia))

        if colchon > 0.0:
            disparo = np.maximum(piso + col_t, pd_dia + col_t)
            bloq = vivo & (eq <= disparo)
            ndisp += bloq
            eq = eq - np.where(bloq, eq * coste_bp / 10000.0, 0.0)
            bloq = np.zeros(n, bool)
        else:
            bloq = np.zeros(n, bool)

        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        # ---- 2. la sesion de la #2 se recorre
        act = np.where(vivo & ~bloq)[0]
        eq_fin = eq.copy()

        if act.size:
            fa = f[act]
            b  = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
            k  = np.arange(1, SUB + 1) / SUB
            br = (b - k[None, :] * b[:, -1:]) * fa[:, None] \
                 + k[None, :] * (g2[act, d] * fa)[:, None]
            camino = eq[act][:, None] + ini_dia[act][:, None] * br

            pico_ac = np.maximum.accumulate(
                np.maximum(camino, hwm[act][:, None]), axis=1)
            piso_ac = np.where(locked[act][:, None],
                               np.maximum(piso[act][:, None], cuenta),
                               np.maximum(piso[act][:, None],
                                          piso_tr_de(pico_ac)))
            piso_ac = np.maximum(piso_ac, pd_dia[act][:, None])

            toca = camino < piso_ac
            i_piso = np.where(toca.any(1), toca.argmax(1), SUB)

            if colchon > 0.0:
                td = camino <= piso_ac + col_t
                i_disp = np.where(td.any(1), td.argmax(1), SUB)
                salvado = (i_disp < i_piso) & (i_disp < SUB)
            else:
                i_disp  = np.full(act.size, SUB)
                salvado = np.zeros(act.size, bool)

            muerto = np.where(salvado, False, i_piso < SUB)
            idx_s  = np.clip(i_disp, 0, SUB - 1)
            eq_s   = camino[np.arange(act.size), idx_s]
            eq_s   = eq_s - eq_s * coste_bp / 10000.0

            eq_fin[act] = np.where(salvado, eq_s, camino[:, -1])
            ndisp[act] += salvado
            vivo[act]   = ~muerto
            pico_hasta = np.take_along_axis(pico_ac, idx_s[:, None], 1)[:, 0]
            hwm[act] = np.where(salvado, np.maximum(hwm[act], pico_hasta),
                                np.maximum(hwm[act], pico_ac[:, -1]))

        # ---- 3. cierre del dia
        vivo = vivo & ~(vivo & (eq_fin < piso_dia))
        pnl  = eq_fin - ini_dia
        bal  = np.where(vivo, eq_fin, bal)
        hwm  = np.where(vivo, np.maximum(hwm, bal), hwm)
        if lock:
            locked = locked | (vivo & (piso_tr_de(hwm) >= cuenta))
        piso = np.where(vivo & locked, np.maximum(piso, cuenta),
                        np.where(vivo, np.maximum(piso, piso_tr_de(hwm)), piso))

        cual  = cual + (vivo & (pnl >= MINBEN * cuenta))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)

        prof = bal - cuenta
        pide = vivo & (prof >= umbral) & (cual >= min_dias)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag  += pide
            bal   = np.where(pide, cuenta, bal)
            hwm   = np.where(pide, cuenta, hwm)
            piso  = np.where(pide, cuenta * (1 - dd), piso)
            locked= np.where(pide, False, locked)
            cual  = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    return dict(neto=extra * SPLIT - cuota, npag=npag, quemada=~vivo,
                ndisp=ndisp, f_medio=np.divide(fsum, np.maximum(fdias, 1)))


# ------------------------------------------------------------------ main
h1, h2, w1, w2, lev = cargar()
sd = h2.std()
g1, g2 = bootstrap_par(h1, h2, DIAS, N)

E = "=" * 88
print(E)
print("EFECTO DE LAS CORRECCIONES DEL PANEL   ·   cuenta 50K, DD 7%, vol 4,5%")
print(E)
print(f"  {'version de las reglas':<46}{'P(quema)':>10}{'P(cobro)':>10}{'EV anual':>12}")
print("  " + "-" * 78)
casos = [
    ("como lo tenia (diario absoluto, 6 dias)",
     dict(relativo=False, min_dias=6)),
    ("solo el diario a relativo",
     dict(relativo=True, min_dias=6)),
    ("solo los dias minimos a 5",
     dict(relativo=False, min_dias=5)),
    ("REGLAS REALES (relativo + 5 dias)",
     dict(relativo=True, min_dias=5)),
    ("REGLAS REALES + escalado ref 5%",
     dict(relativo=True, min_dias=5, escala_ref=0.05)),
]
for nom, kw in casos:
    r = simular(g1, g2, sd, **kw)
    print(f"  {nom:<46}{r['quemada'].mean():>9.1%}"
          f"{(r['npag'] > 0).mean():>10.1%}{r['neto'].mean()/2:>11,.0f}$")

print()
print(E)
print("EL PRODUCTO QUE TIENES AHORA: 25K CON DD DEL 5%")
print(E)
print("  El colchon total es 5%, no 7%. El escalado hay que reescalar con el.")
print(f"\n  {'escala_ref':>11}{'= % del colchon':>17}{'P(quema)':>11}"
      f"{'P(cobro)':>11}{'EV anual':>12}{'tamaño':>9}")
print("  " + "-" * 71)
for ref in (0.0, 0.025, 0.030, 0.035, 0.040, 0.045):
    r = simular(g1, g2, sd, cuenta=25_000.0, dd=0.05, relativo=True,
                min_dias=5, cuota=50.0,
                escala_ref=ref, escala_min=0.25)
    etq = "sin" if ref == 0 else f"{ref:.1%}"
    pct = "-" if ref == 0 else f"{ref/0.05:.0%}"
    print(f"  {etq:>11}{pct:>17}{r['quemada'].mean():>10.1%}"
          f"{(r['npag'] > 0).mean():>11.1%}{r['neto'].mean()/2:>11,.0f}$"
          f"{r['f_medio'].mean():>9.2f}")

print()
print("  Referencia: con DD del 7% el optimo fue ref 5%, o sea el 71% del")
print("  colchon total. El equivalente para un colchon del 5% son 3,5%.")

print()
print(E)
print("5% CONTRA 7%: ¿cuanto cuesta ese 2% de colchon?")
print(E)
print(f"  {'cuenta':>8}{'DD':>6}{'escalado':>10}{'P(quema)':>11}{'P(cobro)':>11}"
      f"{'EV anual':>12}")
print("  " + "-" * 58)
for cuenta, dd, ref, cuota in ((25_000, 0.05, 0.035, 50.0),
                               (25_000, 0.07, 0.050, 50.0),
                               (50_000, 0.05, 0.035, 90.0),
                               (50_000, 0.07, 0.050, 90.0)):
    r = simular(g1, g2, sd, cuenta=float(cuenta), dd=dd, relativo=True,
                min_dias=5, cuota=cuota, escala_ref=ref, escala_min=0.25)
    print(f"  {cuenta:>8,}{dd:>6.0%}{ref:>10.1%}{r['quemada'].mean():>10.1%}"
          f"{(r['npag'] > 0).mean():>11.1%}{r['neto'].mean()/2:>11,.0f}$")
