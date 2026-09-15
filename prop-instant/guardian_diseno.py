#!/usr/bin/env python3
"""
¿QUE DEBE HACER EL GUARDIAN CUANDO EL MARGEN SE ESTRECHA?

La primera version de EA_Guardian cerraba todo y bloqueaba la cuenta. Al
medirlo aparecio un fallo de diseño grave, y conviene dejarlo escrito:

    Si la equity queda POR DEBAJO del nivel de disparo, el bloqueo se
    levanta al dia siguiente, pero la equity sigue por debajo -> el
    Guardian dispara otra vez. Y otra. Es un ESTADO ABSORBENTE: la cuenta
    no se rompe, pero no vuelve a operar nunca, y cada intervencion cobra
    un spread que la empuja al suelo. Con coste cero la cuenta se queda
    congelada (quema 5,8% pero tampoco gana); con el coste real de 3,5 bp
    por intervencion la quema SUBE del 11,4% al 41,3%.

    Es decir: el bloqueo permanente convierte un drawdown recuperable en
    una muerte lenta segura.

Asi que se comparan cuatro diseños:

  A. SIN GUARDIAN
       referencia.

  B. SOLO CIERRE DURO (la version que hay que corregir)
       cerrar todo por encima del suelo y bloquear hasta el reinicio.

  C. SOLO ESCALADO
       no se bloquea nunca. El tamaño de las posiciones se reduce en
       proporcion al margen que queda sobre el suelo del trailing:
           f = recorte(margen / margen_referencia, f_min, 1)
       Asi el presupuesto de riesgo se agota de forma asintotica en vez
       de golpe, y la cuenta conserva capacidad de recuperarse.

  D. ESCALADO + CIERRE DURO con colchon PEQUEÑO
       el escalado gobierna el dia a dia; el cierre duro solo existe como
       ultimo recurso para lo que el escalado no puede prever.

El modelo de los retornos es el mismo del script anterior: la #1 pre-FOMC
llega como HUECO (el Guardian no la ve venir) y la #2 trend se recorre con
un puente browniano de 8 subpasos (el Guardian si la ve). Cada intervencion
de cierre cuesta 3,5 bp de la equity, que es el spread medido de 1,26 bp
por el apalancamiento de x2,67.
"""
import numpy as np
import pandas as pd

RNG    = np.random.default_rng(20260829)
BLOQUE = 5
SUB    = 8
CUENTA = 50_000.0
CUOTA  = 90.0
SPLIT  = 0.90
DD     = 0.07
DD_DIA = 0.04
UMBRAL = 1_000.0
MINDIA = 6
MINBEN = 0.005
BESTDAY= 0.20
DIAS   = 504
N      = 20_000
COSTE  = 3.5      # bp de la equity por intervencion de cierre


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


def simular(g1, g2, sd_sesion, colchon=0.0, colchon_dia=None,
            escala_ref=0.0, escala_min=0.20, coste_bp=COSTE,
            bloquea=True, best_day=BESTDAY):
    """
    colchon    : fraccion del saldo inicial sobre el suelo en que se cierra
                 todo. 0 = sin cierre duro.
    escala_ref : margen (fraccion del saldo inicial) por encima del cual se
                 opera a tamaño pleno. 0 = sin escalado.
    escala_min : suelo del factor de tamaño, para no dejar de operar del todo.
    bloquea    : si True, tras un cierre duro no se opera hasta el dia
                 siguiente (es lo que crea el estado absorbente).
    """
    n, dias = g1.shape
    if colchon_dia is None:
        colchon_dia = colchon * 2.0 / 3.0

    bal   = np.full(n, CUENTA)
    hwm   = np.full(n, CUENTA)
    piso  = np.full(n, CUENTA * (1 - DD))
    lock  = np.zeros(n, bool)
    vivo  = np.ones(n, bool)
    cual  = np.zeros(n, int)
    mejor = np.zeros(n)
    extra = np.zeros(n)
    npag  = np.zeros(n, int)
    ndisp = np.zeros(n, int)
    nhueco= np.zeros(n, int)
    fsum  = np.zeros(n)          # para el factor de tamaño medio
    fdias = np.zeros(n, int)

    col_t = colchon * CUENTA
    col_d = colchon_dia * CUENTA
    paso0 = sd_sesion / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break

        ini_dia  = bal.copy()
        piso_dia = np.maximum(piso, ini_dia - DD_DIA * CUENTA)
        disparo  = np.maximum(piso + col_t,
                              ini_dia - DD_DIA * CUENTA + col_d)

        # ---------- factor de tamaño segun el margen disponible ----------
        if escala_ref > 0.0:
            margen = (ini_dia - piso) / CUENTA
            f = np.clip(margen / escala_ref, escala_min, 1.0)
        else:
            f = np.ones(n)
        fsum  += np.where(vivo, f, 0.0)
        fdias += vivo

        # ---------- 1. el hueco de la #1: instantaneo ----------
        pnl1 = ini_dia * g1[:, d] * f
        eq   = ini_dia + pnl1

        roto  = vivo & (eq < piso_dia)
        nhueco += roto
        vivo  = vivo & ~roto

        if colchon > 0.0:
            bloq = vivo & (eq <= disparo)
            ndisp += bloq
            eq = eq - np.where(bloq, eq * coste_bp / 10000.0, 0.0)
            if not bloquea:
                bloq = np.zeros(n, bool)   # se cierra, pero se puede reabrir
        else:
            bloq = np.zeros(n, bool)

        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        # ---------- 2. la sesion de la #2: con camino ----------
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
            piso_ac = np.where(lock[act][:, None],
                               np.maximum(piso[act][:, None], CUENTA),
                               np.maximum(piso[act][:, None],
                                          pico_ac * (1 - DD)))
            piso_ac = np.maximum(piso_ac,
                                 (ini_dia[act] - DD_DIA * CUENTA)[:, None])

            toca_piso = camino < piso_ac
            i_piso = np.where(toca_piso.any(1), toca_piso.argmax(1), SUB)

            if colchon > 0.0:
                disp_ac = piso_ac + col_t
                toca_disp = camino <= disp_ac
                i_disp = np.where(toca_disp.any(1), toca_disp.argmax(1), SUB)
                # el Guardian tiene que ver la caida en un subpaso ANTERIOR
                # al de la rotura; el empate significa un salto y no salva
                salvado = (i_disp < i_piso) & (i_disp < SUB)
            else:
                i_disp  = np.full(act.size, SUB)
                salvado = np.zeros(act.size, bool)

            muerto = np.where(salvado, False, i_piso < SUB)

            idx_s   = np.clip(i_disp, 0, SUB - 1)
            eq_salv = camino[np.arange(act.size), idx_s]
            eq_salv = eq_salv - eq_salv * coste_bp / 10000.0

            eq_fin[act] = np.where(salvado, eq_salv, camino[:, -1])
            ndisp[act] += salvado
            vivo[act]   = ~muerto

            # el pico solo cuenta hasta donde la equity llego de verdad: si
            # el Guardian cerro en el subpaso i, lo de despues no ocurrio
            pico_hasta = np.take_along_axis(pico_ac, idx_s[:, None], 1)[:, 0]
            hwm[act] = np.where(salvado,
                                np.maximum(hwm[act], pico_hasta),
                                np.maximum(hwm[act], pico_ac[:, -1]))

        # ---------- 3. cierre del dia ----------
        vivo = vivo & ~(vivo & (eq_fin < piso_dia))

        pnl = eq_fin - ini_dia
        bal = np.where(vivo, eq_fin, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm >= CUENTA * (1 + DD)))
        piso = np.where(vivo & lock, np.maximum(piso, CUENTA),
                        np.where(vivo, np.maximum(piso, hwm * (1 - DD)), piso))

        cual  = cual + (vivo & (pnl >= MINBEN * CUENTA))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)

        prof = bal - CUENTA
        pide = vivo & (prof >= UMBRAL) & (cual >= MINDIA)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag  += pide
            bal   = np.where(pide, CUENTA, bal)
            hwm   = np.where(pide, CUENTA, hwm)
            piso  = np.where(pide, CUENTA * (1 - DD), piso)
            lock  = np.where(pide, False, lock)
            cual  = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    return dict(neto=extra * SPLIT - CUOTA, npag=npag, quemada=~vivo,
                ndisp=ndisp, hueco=nhueco,
                f_medio=np.divide(fsum, np.maximum(fdias, 1)))


# ------------------------------------------------------------------ main
h1, h2, w1, w2, lev = cargar()
sd = h2.std()
g1, g2 = bootstrap_par(h1, h2, DIAS, N)

E = "=" * 88
print(E)
print("DISEÑO DEL GUARDIAN: bloquear, escalar, o las dos cosas")
print(E)
print(f"  cuenta {CUENTA:,.0f} · trailing {DD:.0%} · diario {DD_DIA:.0%} · "
      f"{DIAS} sesiones · {N:,} caminos")
print(f"  pesos #1 {w1:.1%} / #2 {w2:.1%} · apalancamiento x{lev:.2f} · "
      f"coste por cierre {COSTE} bp")
print()

casos = [
    ("A  sin Guardian",                 dict()),
    ("B  cierre duro 0,5% + bloqueo",   dict(colchon=0.005)),
    ("B  cierre duro 1,5% + bloqueo",   dict(colchon=0.015)),
    ("B  cierre duro 3,0% + bloqueo",   dict(colchon=0.030)),
    ("B' cierre duro 1,5% SIN bloqueo", dict(colchon=0.015, bloquea=False)),
    ("C  escalado ref 5%, min 0,20",    dict(escala_ref=0.05, escala_min=0.20)),
    ("C  escalado ref 5%, min 0,40",    dict(escala_ref=0.05, escala_min=0.40)),
    ("C  escalado ref 6%, min 0,20",    dict(escala_ref=0.06, escala_min=0.20)),
    ("C  escalado ref 4%, min 0,20",    dict(escala_ref=0.04, escala_min=0.20)),
    ("D  escalado 5%/0,20 + duro 0,5%", dict(escala_ref=0.05, escala_min=0.20,
                                             colchon=0.005, bloquea=False)),
    ("D  escalado 5%/0,20 + duro 1,0%", dict(escala_ref=0.05, escala_min=0.20,
                                             colchon=0.010, bloquea=False)),
]

print(f"  {'diseño':<34}{'P(quema)':>10}{'P(cobro)':>10}{'cobros':>8}"
      f"{'EV anual':>11}{'cierres':>9}{'tamaño':>8}")
print("  " + "-" * 82)
res = {}
for nom, kw in casos:
    r = simular(g1, g2, sd, **kw)
    res[nom] = r
    print(f"  {nom:<34}{r['quemada'].mean():>9.1%}"
          f"{(r['npag'] > 0).mean():>10.1%}{r['npag'].mean():>8.2f}"
          f"{r['neto'].mean()/2:>10,.0f}${r['ndisp'].mean():>9.1f}"
          f"{r['f_medio'].mean():>8.2f}")

print()
print("  'tamaño' es el factor medio de exposicion: 1,00 = tamaño pleno.")
print("  'cierres' son intervenciones de cierre total en 504 sesiones.")

# --------------------------------------------------------------- detalle
print()
print(E)
print("EL MEJOR DISEÑO CONTRA LA REFERENCIA, EN DETALLE")
print(E)
mejor_nom = max((k for k in res if k.startswith(('C', 'D'))),
                key=lambda k: res[k]['neto'].mean() / max(res[k]['quemada'].mean(), 1e-9))
for nom in ("A  sin Guardian", mejor_nom):
    r = res[nom]
    neto = r['neto']
    print(f"\n  {nom}")
    print(f"    EV 2 años {neto.mean():>+10,.0f}$   anual {neto.mean()/2:>+9,.0f}$"
          f"   mediana {np.median(neto):>+10,.0f}$")
    print(f"    percentiles  p10 {np.percentile(neto,10):>+8,.0f}$"
          f"  p25 {np.percentile(neto,25):>+8,.0f}$"
          f"  p75 {np.percentile(neto,75):>+8,.0f}$"
          f"  p90 {np.percentile(neto,90):>+8,.0f}$")
    print(f"    P(cobro) {(r['npag']>0).mean():>6.1%}   "
          f"P(quema) {r['quemada'].mean():>6.1%}   "
          f"P(ni una ni otra) {((r['npag']==0)&~r['quemada']).mean():>6.1%}")
    print(f"    roturas llegadas por hueco nocturno: {r['hueco'].mean():.3f} "
          f"por camino ({r['hueco'].mean()/max(r['quemada'].mean(),1e-9):.0%} "
          f"del total)")

# ------------------------------------------------- sensibilidad a la vol
print()
print(E)
print("SENSIBILIDAD A LA VOLATILIDAD OBJETIVO")
print(E)
print(f"  {'vol':>6}{'diseño':<34}{'P(quema)':>10}{'P(cobro)':>10}{'EV anual':>11}")
print("  " + "-" * 71)
for vol in (0.045, 0.060, 0.070):
    a1, a2, _, _, lv = cargar(vol_objetivo=vol)
    b1, b2 = bootstrap_par(a1, a2, DIAS, 10_000)
    for nom, kw in (("sin Guardian", dict()),
                    ("escalado 5%/0,20", dict(escala_ref=0.05, escala_min=0.20)),
                    ("escalado + duro 0,5%", dict(escala_ref=0.05, escala_min=0.20,
                                                  colchon=0.005, bloquea=False))):
        r = simular(b1, b2, a2.std(), **kw)
        print(f"  {vol:>6.1%}{nom:<34}{r['quemada'].mean():>9.1%}"
              f"{(r['npag']>0).mean():>10.1%}{r['neto'].mean()/2:>10,.0f}$")
    print()
