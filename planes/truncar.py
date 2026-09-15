#!/usr/bin/env python3
"""
¿SE PUEDE SATISFACER LA REGLA DEL 20% TRUNCANDO LA DISTRIBUCION?

La regla de Upcomers: el mejor dia no puede superar el 20% del beneficio total
solicitado. Equivale a exigir  beneficio_total >= 5 x mejor_dia.

La #1 falla por DISPERSION, no por falta de retorno: media 24 bp con
desviacion 63 bp. Cuando llega al umbral es porque uno o dos eventos fueron
grandes, y entonces el mejor dia pasa del 20%.

Hay dos formas de cumplir la regla:
   (a) subir el beneficio total  -> tarda años con 8 eventos y el trailing mata
   (b) BAJAR el mejor dia        -> poner un tope de beneficio por operacion

La (b) no se me habia ocurrido y es contraintuitiva: se renuncia a parte del
retorno esperado para volver la distribucion mas uniforme y hacer la regla
satisfacible. Si el cuello de botella es la regla y no el retorno, puede
compensar.

Se prueba con tope simetrico (take profit y stop loss al mismo nivel) y con
tope solo al beneficio, sobre los 212 eventos reales.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(77)
BLOQUE = 1          # los eventos son independientes: bootstrap simple

EXCL = {pd.Timestamp(x).date() for x in
        ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"]}
f = pd.read_csv("../fomc/fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCL)]["fecha"].dt.date)
ndx = pd.read_csv("../nas100-data/yahoo/NDX.csv", index_col=0, parse_dates=True)
ndx = ndx[["Open", "Close"]].dropna()
ndx = ndx[(ndx > 0).all(axis=1)]
gap = (ndx["Open"] / ndx["Close"].shift(1) - 1.0).dropna()
gap = gap[gap.abs() < 0.10]
ev = gap[pd.Series(gap.index.date, index=gap.index).isin(FOMC)] - 3.4 / 1e4
ev = ev.values

print("=" * 84)
print("LOS 212 EVENTOS REALES, SIN TRUNCAR")
print("=" * 84)
print("  media %.1f bp · sd %.1f bp · min %.1f bp · max %.1f bp"
      % (ev.mean() * 1e4, ev.std() * 1e4, ev.min() * 1e4, ev.max() * 1e4))
print("  ratio mejor/media: %.1f  -> con 8 eventos al año, el mejor dia suele"
      " ser una fraccion grande del total" % (ev.max() / ev.mean()))


def simular(eventos, cuenta, lev, cuota, split, dd_frac, dd_lock,
            best_day, umbral, n_ev_ano=8, anos=3, n=40000):
    """Simula solo los dias de evento: entre ellos no hay posicion."""
    dias = int(n_ev_ano * anos)
    idx = RNG.integers(0, len(eventos), size=(n, dias))
    R = eventos[idx] * lev

    bal = np.full(n, cuenta)
    hwm = np.full(n, cuenta)
    piso = np.full(n, cuenta * (1 - dd_frac))
    lock = np.zeros(n, dtype=bool)
    vivo = np.ones(n, dtype=bool)
    mejor = np.zeros(n)
    ndias = np.zeros(n, dtype=int)
    extra = np.zeros(n)
    cobrado = np.zeros(n, dtype=bool)

    for d in range(dias):
        if not vivo.any():
            break
        pnl = bal * R[:, d]
        nuevo = bal + pnl
        roto = vivo & (nuevo < piso)
        vivo = vivo & ~roto
        if not vivo.any():
            continue
        bal = np.where(vivo, nuevo, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm >= cuenta * (1 + dd_lock)))
        piso = np.where(vivo & lock, np.maximum(piso, cuenta),
                        np.where(vivo, np.maximum(piso, hwm * (1 - dd_frac)),
                                 piso))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        ndias = ndias + (vivo & (pnl > 0))
        prof = bal - cuenta
        pide = vivo & (prof >= umbral) & (ndias >= 6)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra = extra + np.where(pide, prof, 0.0)
            cobrado = cobrado | pide
            bal = np.where(pide, cuenta, bal)
            hwm = np.where(pide, cuenta, hwm)
            piso = np.where(pide, cuenta * (1 - dd_frac), piso)
            lock = np.where(pide, False, lock)
            mejor = np.where(pide, 0.0, mejor)
            ndias = np.where(pide, 0, ndias)
    return dict(p=cobrado.mean(), q=(~vivo).mean(),
                ev=(extra * split).mean() - cuota)


# apalancamiento para llevar la vol de 8 eventos/año al 4,5% anual
sd_ano = ev.std() * np.sqrt(8)
LEV = 0.045 / sd_ano
print("  vol anual de 8 eventos: %.2f%% -> apalancamiento x%.2f para 4,5%%"
      % (sd_ano * 100, LEV))

print()
print("=" * 84)
print("EFECTO DE TRUNCAR  ·  Upcomers: best day 20%, trailing 7%, 6 dias")
print("=" * 84)
print(f"{'tope':<22}{'media':>9}{'sd':>8}{'max':>8}{'P(cobro)':>11}"
      f"{'P(quema)':>11}{'EV':>9}")
print("-" * 84)
CASOS = [("sin tope", None, None),
         ("simetrico +-80 bp", 0.0080, -0.0080),
         ("simetrico +-60 bp", 0.0060, -0.0060),
         ("simetrico +-40 bp", 0.0040, -0.0040),
         ("simetrico +-30 bp", 0.0030, -0.0030),
         ("simetrico +-20 bp", 0.0020, -0.0020),
         ("solo TP +40 bp", 0.0040, None),
         ("solo SL -40 bp", None, -0.0040)]
for nom, tp, sl in CASOS:
    x = ev.copy()
    if tp is not None:
        x = np.minimum(x, tp)
    if sl is not None:
        x = np.maximum(x, sl)
    # se reescala el apalancamiento para mantener 4,5% de vol anual
    sd_x = x.std() * np.sqrt(8)
    lev = 0.045 / sd_x if sd_x > 0 else 0
    r = simular(x, 50_000, lev, 90, 0.90, 0.07, 0.07, 0.20, 1000)
    print(f"{nom:<22}{x.mean()*1e4:>8.1f}{x.std()*1e4:>8.1f}"
          f"{x.max()*1e4:>8.1f}{r['p']:>10.1%}{r['q']:>11.1%}{r['ev']:>9.0f}")

print()
print("=" * 84)
print("CONTROL: los mismos topes SIN la regla del best day")
print("(para separar el efecto de la regla del efecto de truncar)")
print("=" * 84)
print(f"{'tope':<22}{'P(cobro)':>11}{'EV':>9}")
print("-" * 84)
for nom, tp, sl in CASOS[:6]:
    x = ev.copy()
    if tp is not None:
        x = np.minimum(x, tp)
    if sl is not None:
        x = np.maximum(x, sl)
    sd_x = x.std() * np.sqrt(8)
    lev = 0.045 / sd_x if sd_x > 0 else 0
    r = simular(x, 50_000, lev, 90, 0.90, 0.07, 0.07, None, 1000)
    print(f"{nom:<22}{r['p']:>10.1%}{r['ev']:>9.0f}")
