#!/usr/bin/env python3
"""
¿CUANTO COLCHON DEBE DEJAR EL GUARDIAN?

El colchon es el unico parametro libre de EA_Guardian y tiene dos filos:

  * demasiado pequeño -> el Guardian llega tarde y la cuenta se rompe igual;
  * demasiado grande  -> el Guardian cierra en ruido normal, la cuenta se
    queda plana cerca del suelo y nunca recupera. Matas la cuenta tu mismo.

Asi que no se elige por intuicion: se mide.

MODELO — y aqui esta lo que hace este script distinto de los anteriores
---------------------------------------------------------------------
Las dos estrategias NO llegan igual, y eso decide si el Guardian sirve:

  #1 pre-FOMC (72% del riesgo): la posicion se abre a las 15:57 NY y se
     cierra a las 09:30 NY del dia siguiente. Su resultado llega como un
     HUECO. No hay camino intradia que vigilar: el precio ya esta ahi
     cuando el mercado abre. El Guardian NO PUEDE INTERVENIR.
     -> se aplica de golpe y se comprueba la rotura contra el suelo.

  #2 trend (28% del riesgo): posiciones que viven dentro de la sesion.
     Su resultado se recorre con un PUENTE BROWNIANO de 8 subpasos que
     empieza en 0, acaba en el retorno real del dia y tiene la volatilidad
     que le corresponde. El Guardian ve ese camino y puede cortarlo.
     -> aqui el Guardian si actua, y aqui esta tambien su COSTE: cortar
        renuncia al rebote que venia despues dentro del mismo dia.

El puente es el supuesto discutible del script. Los retornos diarios son
reales; el camino de dentro del dia es inventado con la vol correcta. Sin
el, el Guardian saldria gratis y el resultado no valdria nada.

Tambien se modela lo que el Guardian NO puede evitar por construccion:
el suelo del trailing sube con el pico de equity INTRADIA, asi que un
tramo en verde que luego se gira levanta el suelo y no lo baja.
"""
import numpy as np
import pandas as pd

RNG    = np.random.default_rng(20260829)
BLOQUE = 5          # bootstrap por bloques de 5 dias
SUB    = 8          # subpasos intradia para el componente de sesion
CUENTA = 50_000.0
CUOTA  = 90.0
SPLIT  = 0.90
DD     = 0.07       # trailing
DD_DIA = 0.04       # limite diario
UMBRAL = 1_000.0    # minimo para pedir cobro
MINDIA = 6
MINBEN = 0.005
BESTDAY= 0.20
DIAS   = 504        # 2 años
N      = 20_000


# ---------------------------------------------------------------- datos
def cargar(vol_objetivo=0.045, trunc=0.008):
    A = pd.read_csv("../planes/salida/cartera_diaria.csv",
                    index_col=0, parse_dates=True)
    s2 = A["s2"].values
    # los pesos de vol inversa se calculan con la vol SIN truncar, igual que
    # en planes/distribucion.py, para que los numeros sean comparables
    iv1, iv2 = 1 / A["s1"].values.std(), 1 / s2.std()
    s1 = np.clip(A["s1"].values, -trunc, trunc)   # stop y TP de 80 bp
    w1 = iv1 / (iv1 + iv2)
    w2 = 1 - w1
    cart = w1 * s1 + w2 * s2
    lev = vol_objetivo / (cart.std() * np.sqrt(252))
    return w1 * s1 * lev, w2 * s2 * lev, w1, w2, lev


def bootstrap_par(x1, x2, n_dias, n_caminos):
    """Bootstrap por bloques conservando el emparejamiento de los dos dias."""
    nb  = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


# ------------------------------------------------------------ simulacion
def simular(g1, g2, colchon, sd_sesion, colchon_dia=None,
            best_day=BESTDAY, estricto=True, coste_bp=3.5):
    """
    g1 : retornos del componente HUECO (llegan de golpe)
    g2 : retornos del componente SESION (se recorren con puente)
    colchon : fraccion del saldo inicial por encima del suelo en que el
              Guardian cierra. 0.0 = sin Guardian.
    coste_bp: coste de cada intervencion, en bp de la equity. Cerrar cruza
              el spread sobre la exposicion apalancada: el spread medido en
              NACUSD.c fue 1,26 bp y el apalancamiento x2,67, asi que unos
              3,4 bp. Este termino es el que hace que un colchon grande NO
              sea gratis: el numero de intervenciones crece muy rapido.
    """
    if colchon_dia is None:
        colchon_dia = colchon * 2.0 / 3.0     # proporcion 1,5 / 1,0
    n, dias = g1.shape

    bal   = np.full(n, CUENTA)
    hwm   = np.full(n, CUENTA)
    piso  = np.full(n, CUENTA * (1 - DD))
    lock  = np.zeros(n, bool)
    vivo  = np.ones(n, bool)
    cual  = np.zeros(n, int)
    mejor = np.zeros(n)
    extra = np.zeros(n)
    npag  = np.zeros(n, int)
    ndisp = np.zeros(n, int)          # veces que disparo el Guardian
    ndisp_hueco = np.zeros(n, int)    # roturas llegadas por hueco

    col_t = colchon * CUENTA
    col_d = colchon_dia * CUENTA
    paso  = sd_sesion / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break

        ini_dia = bal.copy()
        piso_dia = np.maximum(piso, ini_dia - DD_DIA * CUENTA)   # el que apriete
        disparo  = np.maximum(piso + col_t, ini_dia - DD_DIA * CUENTA + col_d)

        # ---------------- 1. el HUECO de la #1, instantaneo ----------------
        pnl1 = ini_dia * g1[:, d]
        eq   = ini_dia + pnl1

        roto = vivo & (eq < piso_dia)
        ndisp_hueco += roto
        vivo = vivo & ~roto

        # si el hueco ya nos deja por debajo del nivel de disparo, el
        # Guardian cierra en la apertura y el dia se queda plano
        bloq = vivo & (eq <= disparo)
        ndisp += bloq
        eq = eq - np.where(bloq, eq * coste_bp / 10000.0, 0.0)

        # el pico sube con la equity tras el hueco
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        # ---------------- 2. la SESION de la #2, con camino ----------------
        act = np.where(vivo & ~bloq)[0]
        eq_fin = eq.copy()

        if act.size:
            b  = RNG.normal(0.0, paso, size=(act.size, SUB)).cumsum(axis=1)
            k  = np.arange(1, SUB + 1) / SUB
            # puente: empieza en 0, acaba en g2 exactamente
            br = b - k[None, :] * b[:, -1:] + k[None, :] * g2[act, d][:, None]
            camino = eq[act][:, None] + ini_dia[act][:, None] * br

            # el suelo del trailing sube con el pico intradia -> el nivel de
            # disparo tambien. Se recorre el camino de forma acumulativa.
            pico_ac = np.maximum.accumulate(
                np.maximum(camino, hwm[act][:, None]), axis=1)
            piso_ac = np.where(lock[act][:, None],
                               np.maximum(piso[act][:, None], CUENTA),
                               np.maximum(piso[act][:, None],
                                          pico_ac * (1 - DD)))
            piso_ac = np.maximum(piso_ac, (ini_dia[act] - DD_DIA * CUENTA)[:, None])
            disp_ac = piso_ac + col_t

            toca_piso = camino < piso_ac
            toca_disp = camino <= disp_ac

            # primer subpaso en que se toca cada cosa (SUB si nunca)
            i_piso = np.where(toca_piso.any(1), toca_piso.argmax(1), SUB)
            i_disp = np.where(toca_disp.any(1), toca_disp.argmax(1), SUB)

            # ¿llega el Guardian a tiempo?
            #   estricto=True  -> tiene que ver la caida en un subpaso
            #     ANTERIOR al de la rotura. Si ambos ocurren en el mismo
            #     subpaso significa que el precio atraveso disparo y suelo
            #     de un salto, y entonces el Guardian NO salva nada.
            #   estricto=False -> se le concede el empate (optimista).
            if estricto:
                salvado = (i_disp < i_piso) & (i_disp < SUB)
            else:
                salvado = (i_disp <= i_piso) & (i_disp < SUB)
            muerto  = (i_piso < i_disp) | ((i_piso < SUB) & (colchon <= 0.0))

            fin = camino[:, -1]
            idx_disp = np.clip(i_disp, 0, SUB - 1)
            eq_salv  = camino[np.arange(act.size), idx_disp]

            eq_salv = eq_salv - eq_salv * coste_bp / 10000.0
            eq_fin[act] = np.where(salvado, eq_salv, fin)
            ndisp[act] += salvado
            vivo[act]   = ~muerto
            hwm[act]    = np.maximum(hwm[act], pico_ac[:, -1])

        # ---------------- 3. cierre del dia ----------------
        roto2 = vivo & (eq_fin < piso_dia)
        vivo  = vivo & ~roto2

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
                ndisp=ndisp, hueco=ndisp_hueco)


# ------------------------------------------------------------------ main
h1, h2, w1, w2, lev = cargar()
sd_sesion = h2.std()

E = "=" * 84
print(E)
print("CALIBRACION DEL COLCHON DE EA_Guardian")
print(E)
print(f"  cuenta {CUENTA:,.0f} · trailing {DD:.0%} · diario {DD_DIA:.0%} · "
      f"horizonte {DIAS} sesiones")
print(f"  pesos  #1 pre-FOMC {w1:.1%} · #2 trend {w2:.1%} · "
      f"apalancamiento x{lev:.2f}")
print(f"  vol diaria del componente de sesion: {sd_sesion:.4%}  "
      f"(anual {sd_sesion*np.sqrt(252):.2%})")
print(f"  dias con evento FOMC en la serie: {(h1 != 0).sum()} de {len(h1)}")
print(f"  coste cobrado por intervencion: 3,5 bp de la equity "
      f"(spread 1,26 bp x apalancamiento)")
print()

g1, g2 = bootstrap_par(h1, h2, DIAS, N)

filas = []
for col in (0.0, 0.50, 1.00, 1.50, 2.00, 2.50, 3.00, 4.00, 5.00):
    r = simular(g1, g2, col / 100.0, sd_sesion, estricto=True)
    o = simular(g1, g2, col / 100.0, sd_sesion, estricto=False)
    filas.append((col, r, o))

print(f"  {'colchon':>8}{'P(quema)':>11}{'P(cobro)':>11}{'cobros':>9}"
      f"{'EV 2 años':>13}{'EV anual':>12}{'disparos':>10}")
print("  " + "-" * 76)
for col, r, o in filas:
    ev = r['neto'].mean()
    etq = "sin" if col == 0.0 else f"{col:.2f}%"
    print(f"  {etq:>8}{r['quemada'].mean():>10.1%}"
          f"{(r['npag'] > 0).mean():>11.1%}{r['npag'].mean():>9.2f}"
          f"{ev:>12,.0f}${ev/2:>11,.0f}${r['ndisp'].mean():>10.2f}")

print()
print("  El mismo barrido concediendo al Guardian el empate (optimista),")
print("  para ver cuanto del resultado depende de ese supuesto:")
print(f"  {'colchon':>8}{'P(quema) estricto':>19}{'P(quema) optimista':>20}")
print("  " + "-" * 47)
for col, r, o in filas:
    etq = "sin" if col == 0.0 else f"{col:.2f}%"
    print(f"  {etq:>8}{r['quemada'].mean():>18.1%}{o['quemada'].mean():>20.1%}")

print()
print("  Roturas que llegaron por HUECO nocturno (el Guardian no las ve):")
for col, r, o in filas:
    etq = "sin" if col == 0.0 else f"{col:.2f}%"
    print(f"    colchon {etq:>6} -> {r['hueco'].mean():.3f} por camino "
          f"({r['hueco'].mean()/max(r['quemada'].mean(),1e-9):.0%} de las quemas)")

print()
print(E)
print("SENSIBILIDAD: ¿y si el apalancamiento fuera mas alto?")
print(E)
print(f"  {'vol':>6}{'colchon':>9}{'P(quema)':>11}{'P(cobro)':>11}{'EV anual':>12}")
print("  " + "-" * 51)
for vol in (0.045, 0.060, 0.070):
    a1, a2, _, _, lv = cargar(vol_objetivo=vol)
    b1, b2 = bootstrap_par(a1, a2, DIAS, 10_000)
    for col in (0.0, 1.50, 2.50):
        r = simular(b1, b2, col / 100.0, a2.std())
        etq = "sin" if col == 0.0 else f"{col:.2f}%"
        print(f"  {vol:>6.1%}{etq:>9}{r['quemada'].mean():>10.1%}"
              f"{(r['npag'] > 0).mean():>11.1%}"
              f"{r['neto'].mean()/2:>11,.0f}$")
    print()
