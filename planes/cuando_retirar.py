#!/usr/bin/env python3
"""
¿CUANDO HAY QUE RETIRAR?

En todas las simulaciones anteriores puse el umbral de cobro en 1.000 $ y no
lo cuestione nunca. Es un parametro libre y no lo he medido. Aqui se barre.

LA TENSION, en dos frases:
  · Todo beneficio que NO retiras esta en riesgo. El drawdown trailing te
    puede devolver al suelo, y con el suelo bloqueado en el saldo inicial eso
    significa perder TODO el beneficio acumulado y no perder el capital. El
    beneficio no retirado es la parte desprotegida de la cuenta.
  · Pero retirar pronto choca con la regla de consistencia: si el beneficio
    total es pequeño, cualquier dia bueno pasa del 20% y no puedes cobrar.
    Hace falta beneficio ACUMULADO Y REPARTIDO para poder retirarlo.

Y hay una incognita del reglamento que cambia el resultado y que no he podido
verificar: si un cobro reinicia el suelo del drawdown. Se miden los dos casos.

Universo del trend: los 8 mercados CFD. Cuenta de 25K con DD del 7%.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260901)
BLOQUE, SUB = 5, 8
DIAS, N = 504, 20_000
COSTE_BP = 3.5


def cargar(vol_objetivo=0.045, w2=0.30):
    A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
    s1 = np.clip(A["s1"].values, -0.008, 0.008)
    s2 = A["s2"].values
    cart = (1 - w2) * s1 + w2 * s2
    lev = vol_objetivo / (cart.std() * np.sqrt(252))
    return (1 - w2) * s1 * lev, w2 * s2 * lev, lev


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


def simular(g1, g2, sd_sesion, cuenta=25_000.0, dd=0.07, dd_dia=0.04,
            umbral=1_000.0, min_dias=5, min_ben=0.005, best_day=0.20,
            escala_ref=0.05, escala_min=0.25, cuota=50.0,
            reinicia_suelo=True, coste_pago=0.0, split=0.90):
    n, dias = g1.shape
    bal = np.full(n, cuenta); hwm = np.full(n, cuenta)
    piso = np.full(n, cuenta * (1 - dd))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    extra = np.zeros(n); npag = np.zeros(n, int)
    dias_hasta_1 = np.full(n, -1)
    paso0 = sd_sesion / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break
        ini_dia = bal.copy()
        pd_dia = ini_dia * (1 - dd_dia)
        piso_dia = np.maximum(piso, pd_dia)

        margen = (ini_dia - piso) / cuenta
        f = np.clip(margen / escala_ref, escala_min, 1.0)

        eq = ini_dia + ini_dia * g1[:, d] * f
        vivo = vivo & ~(vivo & (eq < piso_dia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        act = np.where(vivo)[0]
        eq_fin = eq.copy()
        if act.size:
            fa = f[act]
            b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
            k = np.arange(1, SUB + 1) / SUB
            br = (b - k[None, :] * b[:, -1:]) * fa[:, None] \
                 + k[None, :] * (g2[act, d] * fa)[:, None]
            camino = eq[act][:, None] + ini_dia[act][:, None] * br
            pico_ac = np.maximum.accumulate(
                np.maximum(camino, hwm[act][:, None]), axis=1)
            piso_ac = np.where(lock[act][:, None],
                               np.maximum(piso[act][:, None], cuenta),
                               np.maximum(piso[act][:, None],
                                          pico_ac * (1 - dd)))
            piso_ac = np.maximum(piso_ac, pd_dia[act][:, None])
            toca = camino < piso_ac
            muerto = toca.any(1)
            eq_fin[act] = camino[:, -1]
            vivo[act] = ~muerto
            hwm[act] = np.maximum(hwm[act], pico_ac[:, -1])

        vivo = vivo & ~(vivo & (eq_fin < piso_dia))
        pnl = eq_fin - ini_dia
        bal = np.where(vivo, eq_fin, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm * (1 - dd) >= cuenta))
        piso = np.where(vivo & lock, np.maximum(piso, cuenta),
                        np.where(vivo, np.maximum(piso, hwm * (1 - dd)), piso))

        cual = cual + (vivo & (pnl >= min_ben * cuenta))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)

        prof = bal - cuenta
        pide = vivo & (prof >= umbral) & (cual >= min_dias)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag += pide
            dias_hasta_1 = np.where(pide & (dias_hasta_1 < 0), d, dias_hasta_1)
            bal = np.where(pide, cuenta, bal)
            if reinicia_suelo:
                hwm = np.where(pide, cuenta, hwm)
                piso = np.where(pide, cuenta * (1 - dd), piso)
                lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    bruto = extra * split
    coste = cuota + npag * coste_pago
    return dict(neto=bruto - coste, npag=npag, quemada=~vivo,
                bruto=bruto, dias1=dias_hasta_1,
                sin_retirar=np.where(vivo, np.maximum(bal - 25_000.0, 0.0), 0.0))


h1, h2, lev = cargar()
g1, g2 = bootstrap_par(h1, h2, DIAS, N)
sd = h2.std()

E = "=" * 92
print(E)
print("BARRIDO DEL UMBRAL DE COBRO  ·  25K, DD 7%, 2 años, cesta CFD")
print(E)
print(f"  apalancamiento x{lev:.2f}  ·  20.000 caminos  ·  cuota 50 $")
print()

for reinicia in (True, False):
    print(f"  {'--- el cobro REINICIA el suelo del drawdown ---' if reinicia else '--- el cobro NO reinicia el suelo (peor caso) ---'}")
    print(f"  {'umbral':>10}{'P(cobro)':>10}{'cobros':>8}{'1er cobro':>11}"
          f"{'EV anual':>11}{'mediana':>10}{'P(quema)':>10}"
          f"{'sin retirar':>13}")
    print("  " + "-" * 83)
    for u in (250, 500, 1_000, 2_000, 3_000, 5_000, 1e12):
        r = simular(g1, g2, sd, umbral=u, reinicia_suelo=reinicia)
        d1 = r['dias1'][r['dias1'] >= 0]
        etq = "nunca" if u > 1e11 else f"{u:,.0f}"
        print(f"  {etq:>10}{(r['npag']>0).mean():>10.1%}{r['npag'].mean():>8.2f}"
              f"{(np.median(d1) if len(d1) else np.nan):>10.0f}d"
              f"{r['neto'].mean()/2:>10,.0f}${np.median(r['neto']):>9,.0f}$"
              f"{r['quemada'].mean():>10.1%}"
              f"{r['sin_retirar'].mean():>12,.0f}$")
    print()

print(E)
print("EL COSTE DE ESPERAR: ¿cuanto beneficio se queda expuesto?")
print(E)
print("  'sin retirar' es el beneficio que sigue dentro de la cuenta al final")
print("  de los 2 años. Con el suelo bloqueado en el saldo inicial, TODO eso")
print("  es perdible: puedes caer hasta 25.000 sin romper nada.")
print()

r_opt = simular(g1, g2, sd, umbral=1_000.0)
r_never = simular(g1, g2, sd, umbral=1e12)
print(f"  retirando con 1.000 $ de beneficio:")
print(f"    retirado (bruto x0,90) : {r_opt['bruto'].mean():>10,.0f} $")
print(f"    aun dentro al final    : {r_opt['sin_retirar'].mean():>10,.0f} $")
print(f"  sin retirar nunca:")
print(f"    retirado               : {r_never['bruto'].mean():>10,.0f} $")
print(f"    aun dentro al final    : {r_never['sin_retirar'].mean():>10,.0f} $")
print(f"    de eso, tu 90%         : {r_never['sin_retirar'].mean()*0.9:>10,.0f} $")

print()
print(E)
print("SENSIBILIDAD AL COSTE DEL MODULO DE PAGOS MENSUALES (13 $/mes)")
print(E)
print("  Si cobras a menudo hay que pagar el modulo. 13 $/mes = 312 $ en 2 años.")
print(f"  {'umbral':>10}{'cobros':>9}{'EV sin coste':>15}{'EV con 312 $':>15}")
print("  " + "-" * 49)
for u in (250, 500, 1_000, 2_000):
    a = simular(g1, g2, sd, umbral=u)
    print(f"  {u:>10,}{a['npag'].mean():>9.2f}{a['neto'].mean()/2:>14,.0f}$"
          f"{(a['neto'].mean()-312)/2:>14,.0f}$")
