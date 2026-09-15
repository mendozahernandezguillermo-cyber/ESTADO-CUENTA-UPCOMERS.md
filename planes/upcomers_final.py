#!/usr/bin/env python3
"""
CONFIGURACION DEFINITIVA EN UPCOMERS VANGUARD

Reglas confirmadas por el centro de ayuda de Upcomers (capturas del usuario):
   - overnight permitido
   - FIN DE SEMANA permitido, tambien en cuentas financiadas
   - EAs permitidos sin restricciones
   - trailing 7% con lock, diario 4%, split 90%, cuota unica
   - best day 20% (pendiente de confirmar en su centro de ayuda para el
     producto de CFD; el 20% esta documentado para el de futuros)

Como el fin de semana esta permitido, la #2 (trend) vuelve al plan y la cartera
es la de dos estrategias.

Se calcula:
   1. la cartera en Upcomers a distintas volatilidades
   2. cuanto cuesta exactamente la regla del best day (con y sin ella)
   3. si truncar la cola de la #1 sigue aportando algo ahora que la #2 aporta
      los dias de actividad
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(4242)
BLOQUE = 5


def bootstrap(fuente, n_dias, n_caminos):
    x = np.asarray(fuente)
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x) - BLOQUE, size=(n_caminos, nb))
    idx = ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
    return x[idx].reshape(n_caminos, -1)[:, :n_dias]


def simular(ret, cuenta=50_000, cuota=90, split=0.90, dd_frac=0.07,
            dd_lock=0.07, dd_dia=0.04, min_dias=6, min_ben=0.005,
            best_day=0.20, umbral=1000):
    n, dias = ret.shape
    bal = np.full(n, cuenta)
    hwm = np.full(n, cuenta)
    piso = np.full(n, cuenta * (1 - dd_frac))
    lock = np.zeros(n, dtype=bool)
    vivo = np.ones(n, dtype=bool)
    cual = np.zeros(n, dtype=int)
    mejor = np.zeros(n)
    extra = np.zeros(n)
    cobrado = np.zeros(n, dtype=bool)
    for d in range(dias):
        if not vivo.any():
            break
        pnl = bal * ret[:, d]
        nuevo = bal + pnl
        roto = vivo & ((nuevo < piso) | (pnl < -dd_dia * bal))
        vivo = vivo & ~roto
        if not vivo.any():
            continue
        bal = np.where(vivo, nuevo, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm >= cuenta * (1 + dd_lock)))
        piso = np.where(vivo & lock, np.maximum(piso, cuenta),
                        np.where(vivo, np.maximum(piso, hwm * (1 - dd_frac)),
                                 piso))
        cual = cual + (vivo & (pnl >= min_ben * cuenta))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof = bal - cuenta
        pide = vivo & (prof >= umbral) & (cual >= min_dias)
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
    return dict(p=cobrado.mean(), q=(~vivo).mean(),
                ev=(extra * split).mean() - cuota)


A = pd.read_csv("salida/cartera_diaria.csv", index_col=0, parse_dates=True)

print("=" * 88)
print("1. LA CARTERA #1+#2 EN UPCOMERS  ·  2 años, bootstrap de retornos reales")
print("=" * 88)
base = A["cartera"].values
sd = base.std() * np.sqrt(252)
R = bootstrap(base, 504, 30000)
print("  vol natural de la cartera: %.2f%%" % (sd * 100))
print()
print(f"{'vol objetivo':>13}{'apalanc.':>10}{'P(cobro)':>11}{'P(quema)':>11}"
      f"{'EV/cuenta':>12}")
print("-" * 88)
best = None
for vol in (0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.07):
    r = simular(R * (vol / sd))
    print(f"{vol:>12.1%}{vol/sd:>10.2f}{r['p']:>10.1%}{r['q']:>11.1%}"
          f"{r['ev']:>12.0f}")
    if best is None or r["ev"] > best[1]:
        best = (vol, r["ev"], r)
print(f"   -> EV maximo en vol {best[0]:.1%}: {best[1]:.0f} $"
      f" (cobro {best[2]['p']:.1%}, quema {best[2]['q']:.1%})")

print()
print("=" * 88)
print("2. CUANTO CUESTA LA REGLA DEL BEST DAY")
print("=" * 88)
print(f"{'vol':>8}{'con 20%':>22}{'con 50%':>22}{'sin regla':>22}")
print(f"{'':>8}{'cobro':>10}{'EV':>12}{'cobro':>10}{'EV':>12}"
      f"{'cobro':>10}{'EV':>12}")
print("-" * 88)
for vol in (0.035, 0.045, 0.06):
    fila = ""
    for bd in (0.20, 0.50, None):
        r = simular(R * (vol / sd), best_day=bd)
        fila += f"{r['p']:>10.1%}{r['ev']:>12.0f}"
    print(f"{vol:>8.1%}{fila}")

print()
print("=" * 88)
print("3. ¿SIGUE APORTANDO TRUNCAR LA COLA DE LA #1?")
print("   (ahora la #2 ya aporta los dias de actividad)")
print("=" * 88)
w1 = A["s1"].std() and (1 / A["s1"].std()) / ((1 / A["s1"].std()) + (1 / A["s2"].std()))
w2 = 1 - w1
print("  pesos: #1 %.0f%%  #2 %.0f%%" % (w1 * 100, w2 * 100))
print()
print(f"{'tope en la #1':<22}{'P(cobro)':>11}{'P(quema)':>11}{'EV':>10}")
print("-" * 88)
for nom, tp in [("sin tope", None), ("+-80 bp", 0.0080),
                ("+-40 bp", 0.0040), ("+-20 bp", 0.0020)]:
    s1 = A["s1"].values.copy()
    if tp:
        s1 = np.clip(s1, -tp, tp)
    cart = w1 * s1 + w2 * A["s2"].values
    sdc = cart.std() * np.sqrt(252)
    Rc = bootstrap(cart, 504, 30000)
    r = simular(Rc * (0.045 / sdc))
    print(f"{nom:<22}{r['p']:>10.1%}{r['q']:>11.1%}{r['ev']:>10.0f}")

print()
print("=" * 88)
print("RESUMEN PARA DECIDIR")
print("=" * 88)
r45 = simular(R * (0.045 / sd))
print("  Configuracion recomendada: vol objetivo 4,5%%, apalancamiento x%.2f"
      % (0.045 / sd))
print("     P(cobro) %.1f%%  ·  P(quema) %.1f%%  ·  EV %+.0f $ por cuenta"
      % (r45["p"] * 100, r45["q"] * 100, r45["ev"]))
print()
print("  Presupuesto de volatilidad por estrategia:")
print("     EA #1 pre-FOMC : %.2f%%  (%.0f%% del riesgo)" % (0.045 * w1, w1 * 100))
print("     EA #2 trend    : %.2f%%  (%.0f%% del riesgo)" % (0.045 * w2, w2 * 100))
