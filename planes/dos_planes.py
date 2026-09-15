#!/usr/bin/env python3
"""
LOS DOS PLANES EN PARALELO, con retornos REALES en vez de gaussianos.

Mejora metodologica sobre todas las simulaciones anteriores: se usa BOOTSTRAP
POR BLOQUES de retornos observados (bloques de 5 dias, para conservar la
autocorrelacion y el agrupamiento de volatilidad). Las gaussianas subestiman
las colas, que es exactamente lo que mata una cuenta con drawdown trailing.

PLAN 1 · UPCOMERS VANGUARD con la cartera validada (#1 pre-FOMC + #2 trend)
   reglas: trailing 7% sobre equity con lock al +7%, diario 4%, cuota unica
   90 $, split 90%, 6 dias cualificados de >=0,5%, best day 20%
   retornos: bootstrap de la serie DIARIA real de la cartera

PLAN 2 · APEX sin ventaja, buscando MINIMIZAR la probabilidad de quemar
   reglas: trailing 5% (2.500 $) que se CONGELA al alcanzar +5%, objetivo de
   evaluacion 3.000 $, luego 5 dias cualificados, consistencia 50%, retiro
   minimo 500 $, split 100%, cuota unica
   retornos: bootstrap del NASDAQ de los ULTIMOS 4 AÑOS (2022-2026) con signo
   aleatorio -> media cero con colas reales. Es la definicion honesta de
   "operar sin ventaja en el mercado actual".

   El hallazgo estructural que se prueba: el trailing de Apex DEJA de seguir
   al equity cuando el nivel de ruina alcanza el balance inicial. Llegar a
   +5% deja un colchon PERMANENTE de 2.500 $. Asi que una politica de dos
   fases -- arriesgar hasta el lock, desapalancar despues -- deberia bajar
   mucho la probabilidad de quemar.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(2026)
BLOQUE = 5


def bootstrap(fuente, n_dias, n_caminos, signo_aleatorio=False):
    """Bootstrap por bloques. Devuelve (n_caminos, n_dias)."""
    x = np.asarray(fuente)
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x) - BLOQUE, size=(n_caminos, nb))
    idx = ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
    out = x[idx]                                   # (caminos, nb, BLOQUE)
    if signo_aleatorio:
        # el signo se aplica ANTES de aplanar y truncar
        s = RNG.choice([-1.0, 1.0], size=(n_caminos, nb))
        out = out * s[:, :, None]
    return out.reshape(n_caminos, -1)[:, :n_dias]


def simular(ret, cuenta, cuota, split, dd_frac, dd_lock, dd_dia,
            objetivo, min_dias, min_ben, best_day, umbral_retiro,
            politica=None):
    """
    ret: matriz (caminos, dias) de retornos FRACCIONALES ya escalados.
    politica: None = tamaño constante. 'dos_fases' = escala x1 hasta el lock
              y luego x0,25.
    dd_lock: nivel al que el trailing se congela, como fraccion (Apex: 0.05).
             None = no se congela nunca.
    Devuelve dict con probabilidades y EV.
    """
    n, dias = ret.shape
    bal = np.full(n, cuenta)
    hwm = np.full(n, cuenta)
    piso = np.full(n, cuenta * (1 - dd_frac))
    lock = np.zeros(n, dtype=bool)
    vivo = np.ones(n, dtype=bool)
    fase = np.zeros(n, dtype=int)        # 0 = evaluacion, 1 = financiada
    cual = np.zeros(n, dtype=int)
    mejor = np.zeros(n)
    extra = np.zeros(n)
    cobrado = np.zeros(n, dtype=bool)

    for d in range(dias):
        if not vivo.any():
            break
        esc = np.ones(n)
        if politica == "dos_fases":
            esc = np.where(lock, 0.25, 1.0)
        pnl = bal * ret[:, d] * esc
        nuevo = bal + pnl

        roto = vivo & ((nuevo < piso) | (pnl < -dd_dia * bal))
        vivo = vivo & ~roto
        if not vivo.any():
            continue

        bal = np.where(vivo, nuevo, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        if dd_lock is not None:
            lock = lock | (vivo & (hwm >= cuenta * (1 + dd_lock)))
            piso = np.where(vivo & lock, np.maximum(piso, cuenta),
                            np.where(vivo, np.maximum(piso, hwm * (1 - dd_frac)),
                                     piso))
        else:
            piso = np.where(vivo, np.maximum(piso, hwm * (1 - dd_frac)), piso)

        cual = cual + (vivo & (pnl >= min_ben * cuenta))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof = bal - cuenta

        if objetivo:
            pasa = vivo & (fase == 0) & (prof >= objetivo * cuenta)
            fase = np.where(pasa, 1, fase)
            cual = np.where(pasa, 0, cual)
            mejor = np.where(pasa, 0.0, mejor)

        pide = vivo & (fase == (1 if objetivo else 0)) \
            & (prof >= umbral_retiro) & (cual >= min_dias)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra = extra + np.where(pide, prof, 0.0)
            cobrado = cobrado | pide
            bal = np.where(pide, cuenta, bal)
            hwm = np.where(pide, cuenta, hwm)
            piso = np.where(pide, cuenta * (1 - dd_frac), piso)
            lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    return dict(p_cobro=cobrado.mean(), p_quema=(~vivo).mean(),
                ev=(extra * split).mean() - cuota, pagos=extra.mean())


# =====================================================================
# PLAN 1 · UPCOMERS VANGUARD con la cartera validada
# =====================================================================
A = pd.read_csv("salida/cartera_diaria.csv", index_col=0, parse_dates=True)
base = A["cartera"].values
sd_base = base.std() * np.sqrt(252)

print("=" * 90)
print("PLAN 1 · UPCOMERS VANGUARD 50K con la cartera validada")
print("bootstrap por bloques de la serie diaria real (vol natural %.2f%%)"
      % (sd_base * 100))
print("=" * 90)
print(f"{'vol objetivo':>13}{'apalanc.':>10}{'P(cobro)':>11}{'P(quema)':>11}"
      f"{'EV/cuenta':>12}")
print("-" * 90)
R = bootstrap(base, 504, 20000)          # 2 años
for vol in (0.02, 0.03, 0.04, 0.045, 0.06, 0.08):
    r = simular(R * (vol / sd_base), 50_000, 90, 0.90,
                dd_frac=0.07, dd_lock=0.07, dd_dia=0.04,
                objetivo=None, min_dias=6, min_ben=0.005,
                best_day=0.20, umbral_retiro=1000)
    print(f"{vol:>12.1%}{vol/sd_base:>10.2f}{r['p_cobro']:>10.1%}"
          f"{r['p_quema']:>11.1%}{r['ev']:>12.0f}")

# =====================================================================
# PLAN 2 · APEX sin ventaja: politicas para minimizar la quema
# =====================================================================
ndx = pd.read_csv("../nas100-data/yahoo/NDX.csv", index_col=0, parse_dates=True)
r_ndx = ndx["Close"].pct_change().dropna()
r4 = r_ndx[r_ndx.index.year >= 2022].values
sd4 = r4.std() * np.sqrt(252)

print()
print("=" * 90)
print("PLAN 2 · APEX 50K SIN VENTAJA · retornos reales del NASDAQ 2022-2026")
print("(vol del mercado en esos 4 años: %.1f%% anual · signo aleatorio ->"
      " media cero)" % (sd4 * 100))
print("=" * 90)
print()
print("  A · TAMAÑO CONSTANTE")
print(f"  {'vol objetivo':>13}{'P(cobro)':>11}{'P(QUEMA)':>11}{'EV':>10}")
print("  " + "-" * 50)
RA = bootstrap(r4, 504, 20000, signo_aleatorio=True)
mejor_a = None
for vol in (0.03, 0.05, 0.08, 0.12, 0.20):
    r = simular(RA * (vol / sd4), 50_000, 50, 1.00,
                dd_frac=0.05, dd_lock=0.05, dd_dia=0.99,
                objetivo=0.06, min_dias=5, min_ben=0.001,
                best_day=0.50, umbral_retiro=500)
    print(f"  {vol:>12.1%}{r['p_cobro']:>10.1%}{r['p_quema']:>11.1%}"
          f"{r['ev']:>10.0f}")
    if mejor_a is None or r["ev"] > mejor_a[1]:
        mejor_a = (vol, r["ev"], r)

print()
print("  B · DOS FASES: arriesgar hasta que el trailing se CONGELA (+5%),")
print("      y despues desapalancar a un cuarto del tamaño")
print(f"  {'vol inicial':>13}{'P(cobro)':>11}{'P(QUEMA)':>11}{'EV':>10}"
      f"{'vs A':>9}")
print("  " + "-" * 60)
for vol in (0.03, 0.05, 0.08, 0.12, 0.20):
    r = simular(RA * (vol / sd4), 50_000, 50, 1.00,
                dd_frac=0.05, dd_lock=0.05, dd_dia=0.99,
                objetivo=0.06, min_dias=5, min_ben=0.001,
                best_day=0.50, umbral_retiro=500, politica="dos_fases")
    ra = simular(RA * (vol / sd4), 50_000, 50, 1.00,
                 dd_frac=0.05, dd_lock=0.05, dd_dia=0.99,
                 objetivo=0.06, min_dias=5, min_ben=0.001,
                 best_day=0.50, umbral_retiro=500)
    d = r["p_quema"] - ra["p_quema"]
    print(f"  {vol:>12.1%}{r['p_cobro']:>10.1%}{r['p_quema']:>11.1%}"
          f"{r['ev']:>10.0f}{d:>+8.1%}")

print()
print("  C · ¿Y SI EL TRAILING NO SE CONGELARA?  (control de la hipotesis)")
print(f"  {'vol objetivo':>13}{'P(cobro)':>11}{'P(QUEMA)':>11}{'EV':>10}")
print("  " + "-" * 50)
for vol in (0.05, 0.08, 0.12):
    r = simular(RA * (vol / sd4), 50_000, 50, 1.00,
                dd_frac=0.05, dd_lock=None, dd_dia=0.99,
                objetivo=0.06, min_dias=5, min_ben=0.001,
                best_day=0.50, umbral_retiro=500)
    print(f"  {vol:>12.1%}{r['p_cobro']:>10.1%}{r['p_quema']:>11.1%}"
          f"{r['ev']:>10.0f}")
print()
print("  Si el lock explica la diferencia, la fila C debe quemar mucho mas.")
