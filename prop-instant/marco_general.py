#!/usr/bin/env python3
"""
MARCO GENERAL — evaluar CUALQUIER estrategia contra CUALQUIER prop firm.

Nada depende del EA del NASDAQ. La estrategia entra como (Sharpe bruto anual,
volatilidad anual, exposicion nocturna, forma de la cola). La firma entra como
un conjunto de reglas. La cartera entra como (N cuentas, correlacion rho).

tipo_dd:
  'static'      nivel fijo desde el balance inicial de la fase
  'trail_eod'   sigue el maximo de balance AL CIERRE, se topa en el inicial
  'trail_rt'    sigue el maximo de equity en TIEMPO REAL (peor caso)
  'trail_lock'  como trail_rt pero se congela al alcanzar +dd_max
"""
import numpy as np
from dataclasses import dataclass

DIAS_ANO = 252
SUB      = 4


@dataclass
class Reglas:
    nombre:        str
    cuenta:        float = 50_000.0
    cuota:         float = 90.0
    reembolsable:  bool  = False
    split:         float = 0.90
    dd_dia:        float = 0.04
    dd_max:        float = 0.07
    tipo_dd:       str   = 'trail_lock'
    objetivos:     tuple = ()
    min_dias:      int   = 6
    min_benef_dia: float = 0.005
    best_day:      float = 0.20


FIRMAS = {
    'upcomers_vanguard': Reglas(
        nombre='Upcomers Vanguard (instant)', cuota=90, reembolsable=False,
        split=0.90, dd_dia=0.04, dd_max=0.07, tipo_dd='trail_lock',
        objetivos=(), min_dias=6, min_benef_dia=0.005, best_day=0.20),
    'ftmo_2step': Reglas(
        nombre='FTMO 2-Step', cuota=345, reembolsable=True,
        split=0.80, dd_dia=0.05, dd_max=0.10, tipo_dd='static',
        objetivos=(0.10, 0.05), min_dias=4, min_benef_dia=0.0, best_day=None),
    'ftmo_1step': Reglas(
        nombre='FTMO 1-Step', cuota=300, reembolsable=False,
        split=0.90, dd_dia=0.03, dd_max=0.10, tipo_dd='trail_eod',
        objetivos=(0.10,), min_dias=4, min_benef_dia=0.0, best_day=0.50),
}


def motor(R, sharpe_bruto, vol, umbral, anos=3, n=6_000, n_cuentas=1,
          rho=0.0, recorte=0.252, cola='normal', overnight=0.0, semilla=7):
    rng  = np.random.default_rng(semilla)
    dias = int(anos * DIAS_ANO)
    C    = R.cuenta
    sh   = sharpe_bruto - recorte
    sd_d = vol / np.sqrt(DIAS_ANO) * C          # desviacion DIARIA
    mu_s = sh * vol / (DIAS_ANO * SUB) * C
    sd_s = sd_d / np.sqrt(SUB)

    F = (n, n_cuentas)
    fase     = np.zeros(F, dtype=int)
    ini_fase = np.full(F, C)
    balance  = np.full(F, C)
    hwm_rt   = np.full(F, C)     # maximo de equity intradia
    hwm_eod  = np.full(F, C)     # maximo de balance al cierre
    locked   = np.zeros(F, dtype=bool)
    vivo     = np.ones(F, dtype=bool)
    cual     = np.zeros(F, dtype=int)
    mejor    = np.zeros(F)
    extraido = np.zeros(F)
    cobrado  = np.zeros(F, dtype=bool)
    n_fases  = len(R.objetivos)
    objs     = np.array(R.objetivos + (0.0,))

    def ruina():
        if R.tipo_dd == 'static':
            return ini_fase * (1 - R.dd_max)
        if R.tipo_dd == 'trail_eod':
            return np.minimum(hwm_eod - R.dd_max * C, ini_fase)
        if R.tipo_dd == 'trail_lock':
            return np.where(locked, ini_fase, hwm_rt * (1 - R.dd_max))
        return hwm_rt * (1 - R.dd_max)

    for _ in range(dias):
        if not vivo.any():
            break

        z_com = rng.standard_normal((n, 1, SUB))
        z_idi = rng.standard_normal((n, n_cuentas, SUB))
        z     = np.sqrt(rho) * z_com + np.sqrt(1 - rho) * z_idi
        if cola == 'grid':
            malo = rng.random((n, n_cuentas, 1)) < 0.03
            z    = np.where(malo, -np.abs(z) * 6.0, np.abs(z) * 0.32)

        # posicion arrastrada a las 00:00 UTC: flotante no realizado
        flot   = overnight * sd_d * rng.standard_normal(F)
        eq_ini = balance + flot
        # la regla toma el MAYOR de (equity, balance) como referencia
        ref    = balance + np.maximum(0.0, flot)
        lim_d  = ref * (1 - R.dd_dia)

        eq     = eq_ini[:, :, None] + np.cumsum(mu_s + sd_s * z, axis=2)
        eq_min, eq_max, eq_fin = eq.min(2), eq.max(2), eq[:, :, -1]

        roto = vivo & ((eq_min < ruina()) | (eq_min < lim_d))
        vivo = vivo & ~roto
        act  = vivo
        if not act.any():
            continue

        pnl      = np.where(act, eq_fin - balance, 0.0)
        balance  = np.where(act, eq_fin, balance)
        hwm_rt   = np.where(act, np.maximum(hwm_rt, eq_max), hwm_rt)
        hwm_eod  = np.where(act, np.maximum(hwm_eod, balance), hwm_eod)
        if R.tipo_dd == 'trail_lock':
            locked = locked | (act & (hwm_rt >= ini_fase * (1 + R.dd_max)))

        cual  = cual + (act & (pnl >= R.min_benef_dia * C))
        mejor = np.where(act, np.maximum(mejor, pnl), mejor)
        prof  = balance - ini_fase

        if n_fases:
            obj  = objs[np.minimum(fase, n_fases)]
            pasa = act & (fase < n_fases) & (prof >= obj * C) & \
                   (cual >= R.min_dias)
            if pasa.any():
                fase     = np.where(pasa, fase + 1, fase)
                balance  = np.where(pasa, C, balance)
                ini_fase = np.where(pasa, C, ini_fase)
                hwm_rt   = np.where(pasa, C, hwm_rt)
                hwm_eod  = np.where(pasa, C, hwm_eod)
                locked   = np.where(pasa, False, locked)
                cual     = np.where(pasa, 0, cual)
                mejor    = np.where(pasa, 0.0, mejor)
                prof     = balance - ini_fase

        pide = act & (fase >= n_fases) & (prof >= umbral) & (cual >= R.min_dias)
        if R.best_day is not None:
            pide = pide & (mejor <= R.best_day * np.maximum(prof, 1e-9))

        if pide.any():
            extraido = np.where(pide, extraido + prof, extraido)
            cobrado  = cobrado | pide
            balance  = np.where(pide, ini_fase, balance)
            hwm_rt   = np.where(pide, ini_fase, hwm_rt)
            hwm_eod  = np.where(pide, ini_fase, hwm_eod)
            locked   = np.where(pide, False, locked)
            cual     = np.where(pide, 0, cual)
            mejor    = np.where(pide, 0.0, mejor)

    neto = extraido * R.split - R.cuota
    if R.reembolsable:
        neto = neto + np.where(cobrado, R.cuota, 0.0)
    total = neto.sum(axis=1)
    return dict(ev_cuenta=neto.mean(), ev_cartera=total.mean(),
                p_cobro=cobrado.mean(), p_ruina=(~vivo).mean(),
                p_cartera_pos=(total > 0).mean(), sd_cartera=total.std())


def barrido(clave, sharpes=(0.0, 1.0, 2.0)):
    R = FIRMAS[clave]
    print(f"\n{'=' * 72}")
    print(f"{R.nombre} · cuota {R.cuota:.0f} $ · split {R.split:.0%} · "
          f"dd {R.dd_max:.0%} {R.tipo_dd} · diario {R.dd_dia:.0%}")
    if R.objetivos:
        print(f"objetivos {' + '.join(f'{o:.0%}' for o in R.objetivos)} · "
              f"reembolsable {'SI' if R.reembolsable else 'no'} · "
              f"best day {R.best_day}")
    print('=' * 72)
    print(f"{'Sharpe':>7}{'vol':>7}{'P(cobro)':>11}{'P(ruina)':>11}{'EV/cta':>11}")
    print('-' * 72)
    for sh in sharpes:
        mej = (-1e9, None, None)
        for vol in (0.04, 0.06, 0.08, 0.12, 0.18, 0.25):
            r = motor(R, sh, vol, umbral=0.02 * R.cuenta)
            print(f"{sh:>7.2f}{vol:>7.0%}{r['p_cobro']:>10.1%}"
                  f"{r['p_ruina']:>11.1%}{r['ev_cuenta']:>11.0f}")
            if r['ev_cuenta'] > mej[0]:
                mej = (r['ev_cuenta'], vol, r)
        print(f"{'':>14}-> optimo vol {mej[1]:.0%}  EV {mej[0]:.0f} $  "
              f"P(cobro) {mej[2]['p_cobro']:.1%}")


for k in ('upcomers_vanguard', 'ftmo_2step', 'ftmo_1step'):
    barrido(k)

print(f"\n{'=' * 72}")
print("CORRELACION ENTRE ESTRATEGIAS — N cuentas · Vanguard · Sharpe 1,0 · vol 6%")
print("La firma PROHIBE la misma estrategia en varias cuentas. Esto mide si")
print("ademas te serviria de algo estadisticamente.")
print('=' * 72)
print(f"{'N':>3}{'rho':>7}{'EV cartera':>13}{'sd cartera':>13}{'P(cartera>0)':>15}")
print('-' * 72)
for N in (1, 3, 6):
    for rho in (0.0, 0.5, 1.0):
        r = motor(FIRMAS['upcomers_vanguard'], 1.0, 0.06, umbral=1000,
                  n=4000, n_cuentas=N, rho=rho)
        print(f"{N:>3}{rho:>7.1f}{r['ev_cartera']:>13.0f}"
              f"{r['sd_cartera']:>13.0f}{r['p_cartera_pos']:>15.1%}")

print(f"\n{'=' * 72}")
print("QUE LE HACE UNA GRID/MARTINGALA (misma media y vol, otra cola)")
print('=' * 72)
print(f"{'firma':<30}{'cola':>9}{'P(cobro)':>11}{'P(ruina)':>11}{'EV':>10}")
print('-' * 72)
for k in FIRMAS:
    for cola in ('normal', 'grid'):
        r = motor(FIRMAS[k], 1.0, 0.06, umbral=1000, cola=cola)
        print(f"{FIRMAS[k].nombre:<30}{cola:>9}{r['p_cobro']:>10.1%}"
              f"{r['p_ruina']:>11.1%}{r['ev_cuenta']:>10.0f}")

print(f"\n{'=' * 72}")
print("COSTE DE ARRASTRAR POSICION A LAS 00:00 UTC")
print('=' * 72)
print(f"{'firma':<30}{'overnight':>10}{'P(cobro)':>11}{'P(ruina)':>11}{'EV':>10}")
print('-' * 72)
for k in FIRMAS:
    for ov in (0.0, 0.5, 1.0):
        r = motor(FIRMAS[k], 1.0, 0.06, umbral=1000, overnight=ov)
        print(f"{FIRMAS[k].nombre:<30}{ov:>10.0%}{r['p_cobro']:>10.1%}"
              f"{r['p_ruina']:>11.1%}{r['ev_cuenta']:>10.0f}")
