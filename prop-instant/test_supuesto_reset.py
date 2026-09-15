#!/usr/bin/env python3
"""
El marco dice que Vanguard tiene EV POSITIVO incluso con Sharpe 0.
Eso es economicamente implausible: una firma que vende ese producto pierde
dinero sistematicamente. Asi que uno de mis supuestos esta mal.

El candidato principal: al cobrar, supuse que el Dynamic Risk Shield se
REARMA desde el balance inicial. Si en realidad el nivel de ruina se queda
donde estaba (o solo baja por el importe retirado), el proceso de renovacion
se rompe y los numeros caen.

Aqui se comparan las tres variantes posibles.
"""
import numpy as np
from marco_general import Reglas, FIRMAS, DIAS_ANO, SUB


def motor2(R, sharpe_bruto, vol, umbral, modo_reset, anos=3, n=15_000,
           recorte=0.252, semilla=99):
    """modo_reset: 'rearma' | 'persiste' | 'baja_por_retiro'"""
    rng  = np.random.default_rng(semilla)
    dias = int(anos * DIAS_ANO)
    C    = R.cuenta
    sh   = sharpe_bruto - recorte
    sd_d = vol / np.sqrt(DIAS_ANO) * C
    mu_s = sh * vol / (DIAS_ANO * SUB) * C
    sd_s = sd_d / np.sqrt(SUB)

    balance = np.full(n, C)
    hwm     = np.full(n, C)
    piso    = np.full(n, C * (1 - R.dd_max))   # nivel de ruina explicito
    locked  = np.zeros(n, dtype=bool)
    vivo    = np.ones(n, dtype=bool)
    cual    = np.zeros(n, dtype=int)
    mejor   = np.zeros(n)
    extraido= np.zeros(n)
    cobrado = np.zeros(n, dtype=bool)
    n_pagos = np.zeros(n, dtype=int)

    for _ in range(dias):
        if not vivo.any():
            break
        z   = rng.standard_normal((n, SUB))
        eq  = balance[:, None] + np.cumsum(mu_s + sd_s * z, axis=1)
        emin, emax, efin = eq.min(1), eq.max(1), eq[:, -1]
        lim_d = balance * (1 - R.dd_dia)

        roto = vivo & ((emin < piso) | (emin < lim_d))
        vivo = vivo & ~roto
        if not vivo.any():
            continue

        pnl     = np.where(vivo, efin - balance, 0.0)
        balance = np.where(vivo, efin, balance)
        hwm     = np.where(vivo, np.maximum(hwm, emax), hwm)
        locked  = locked | (vivo & (hwm >= C * (1 + R.dd_max)))
        piso    = np.where(vivo & ~locked,
                           np.maximum(piso, hwm * (1 - R.dd_max)), piso)
        piso    = np.where(vivo & locked, np.maximum(piso, C), piso)

        cual  = cual + (vivo & (pnl >= R.min_benef_dia * C))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof  = balance - C

        pide = vivo & (prof >= umbral) & (cual >= R.min_dias)
        if R.best_day is not None:
            pide = pide & (mejor <= R.best_day * np.maximum(prof, 1e-9))

        if pide.any():
            retiro   = np.where(pide, prof, 0.0)
            extraido = extraido + retiro
            n_pagos  = n_pagos + pide
            cobrado  = cobrado | pide
            balance  = np.where(pide, C, balance)
            cual     = np.where(pide, 0, cual)
            mejor    = np.where(pide, 0.0, mejor)
            if modo_reset == 'rearma':
                hwm    = np.where(pide, C, hwm)
                piso   = np.where(pide, C * (1 - R.dd_max), piso)
                locked = np.where(pide, False, locked)
            elif modo_reset == 'persiste':
                hwm    = np.where(pide, C, hwm)      # el piso NO se toca
            elif modo_reset == 'baja_por_retiro':
                hwm    = np.where(pide, C, hwm)
                piso   = np.where(pide, piso - retiro, piso)

    neto = extraido * R.split - R.cuota
    if R.reembolsable:
        neto = neto + np.where(cobrado, R.cuota, 0.0)
    return dict(ev=neto.mean(), p=cobrado.mean(), r=(~vivo).mean(),
                pagos=n_pagos.mean())


R = FIRMAS['upcomers_vanguard']
print("=" * 74)
print("SENSIBILIDAD AL SUPUESTO DE REARME DEL SHIELD TRAS COBRAR")
print("Upcomers Vanguard 50K · umbral de retiro 1.000 $ · 3 anos")
print("=" * 74)
print(f"{'Sharpe':>7}{'vol':>6}{'modo de reset':>20}{'P(cobro)':>11}"
      f"{'pagos':>8}{'P(ruina)':>11}{'EV':>9}")
print("-" * 74)
for sh in (0.0, 1.0, 2.0):
    for vol in (0.06, 0.08):
        for modo in ('rearma', 'baja_por_retiro', 'persiste'):
            r = motor2(R, sh, vol, 1000, modo)
            print(f"{sh:>7.2f}{vol:>6.0%}{modo:>20}{r['p']:>10.1%}"
                  f"{r['pagos']:>8.2f}{r['r']:>11.1%}{r['ev']:>9.0f}")
        print()

print("=" * 74)
print("LECTURA: si el piso NO se rearma, el proceso de renovacion desaparece")
print("y el EV con Sharpe 0 deberia acercarse a la cuota perdida (-90 $).")
print("Ese es el supuesto que hay que verificar ANTES de pagar nada.")
