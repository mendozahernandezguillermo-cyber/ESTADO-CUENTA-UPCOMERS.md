#!/usr/bin/env python3
"""
Simulacion de cuenta INSTANT FUNDING 50K, cuota UNICA de 90 USD.
Reglas segun lo indicado por el usuario:
  - perdida maxima diaria  5%  = 2.500
  - drawdown maximo total  7%  = 3.500   (se simula ESTATICO y TRAILING)
Hito de cobro: 3.000 de beneficio (6%). Reparto 80/20 -> 2.400 netos.
Se anade la regla de consistencia (mejor dia <= X% del beneficio total).

Parametrizado por Sharpe ANUAL VERDADERO y volatilidad anual, no por
los numeros del NASDAQ: el objetivo es que sirva para cualquier
instrumento (oro, divisas, indices europeos...).
"""
import numpy as np

RNG      = np.random.default_rng(20260829)
CUENTA   = 50_000.0
LIM_DIA  = 0.05 * CUENTA      # 2.500
LIM_DD   = 0.07 * CUENTA      # 3.500
OBJETIVO = 0.06 * CUENTA      # 3.000
SPLIT    = 0.80
CUOTA    = 90.0
DIAS_ANO = 252
N        = 40_000


def simular(sharpe, vol_anual, dias=DIAS_ANO, trailing=False,
            consistencia=None, coste_diario_bp=0.0, n=N):
    """Devuelve (p_cobro, p_quema, p_nada, p_bloqueado_consistencia, ev)."""
    mu_d    = (sharpe * vol_anual) / DIAS_ANO * CUENTA
    sd_d    = vol_anual / np.sqrt(DIAS_ANO) * CUENTA
    coste_d = coste_diario_bp / 10_000.0 * CUENTA

    pnl = RNG.normal(mu_d - coste_d, sd_d, size=(n, dias))

    equity   = np.cumsum(pnl, axis=1)
    pico     = np.maximum.accumulate(np.maximum(equity, 0.0), axis=1)

    # --- condiciones de ruina ---
    ruina_dd  = (equity < -LIM_DD) if not trailing else ((pico - equity) > LIM_DD)
    ruina_dia = pnl < -LIM_DIA
    ruina     = ruina_dd | ruina_dia
    exito     = equity >= OBJETIVO

    # primer dia en que ocurre cada cosa (dias+1 = nunca)
    def primer(mask):
        hay = mask.any(axis=1)
        idx = np.where(hay, mask.argmax(axis=1), dias + 1)
        return idx

    t_ruina = primer(ruina)
    t_exito = primer(exito)

    cobra  = t_exito < t_ruina
    quema  = t_ruina < t_exito
    nada   = (t_exito > dias) & (t_ruina > dias)

    # --- regla de consistencia, evaluada el dia del cobro ---
    bloq = np.zeros(n, dtype=bool)
    if consistencia is not None:
        ganan = np.where(pnl > 0, pnl, 0.0)
        idx   = np.clip(t_exito, 0, dias - 1)
        filas = np.arange(n)
        # mejor dia y beneficio total hasta el dia del cobro
        mejor = np.array([ganan[i, :idx[i] + 1].max() if cobra[i] else 0.0
                          for i in filas])
        total = np.array([equity[i, idx[i]] if cobra[i] else 1.0
                          for i in filas])
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = np.where(total > 0, mejor / total, 0.0)
        bloq = cobra & (ratio > consistencia)

    cobra_ok = cobra & ~bloq
    ev = cobra_ok.mean() * OBJETIVO * SPLIT - CUOTA
    return (cobra_ok.mean(), quema.mean(), nada.mean(), bloq.mean(), ev)


def tabla(titulo, filas, **kw):
    print(f"\n{titulo}")
    print(f"{'esc':<22}{'cobra':>9}{'quema':>9}{'nada':>9}{'bloq':>9}{'EV $':>10}")
    print("-" * 68)
    for etiq, sh, vol in filas:
        c, q, n_, b, ev = simular(sh, vol, **kw)
        print(f"{etiq:<22}{c:>8.1%}{q:>9.1%}{n_:>9.1%}{b:>9.1%}{ev:>10.0f}")


print("=" * 68)
print("CUENTA INSTANT 50K · cuota unica 90 $ · DD 7% · dia 5% · objetivo 6%")
print("=" * 68)

vols = [0.05, 0.10, 0.15, 0.20, 0.30, 0.45]

# ---------- 1. sin ninguna ventaja (Sharpe verdadero = 0) ----------
tabla("1) SIN VENTAJA (Sharpe real 0) · DD estatico · 12 meses",
      [(f"vol {v:.0%}", 0.0, v) for v in vols],
      trailing=False)

tabla("2) SIN VENTAJA (Sharpe real 0) · DD TRAILING · 12 meses",
      [(f"vol {v:.0%}", 0.0, v) for v in vols],
      trailing=True)

# ---------- 3. con ventaja real ----------
for sh in [0.5, 1.0, 2.0]:
    tabla(f"3) Sharpe real {sh} · DD estatico · 12 meses",
          [(f"vol {v:.0%}", sh, v) for v in vols],
          trailing=False)

# ---------- 4. efecto del coste de transaccion ----------
tabla("4) SIN VENTAJA + coste 1,5 bp/dia (spread prop) · estatico",
      [(f"vol {v:.0%}", 0.0, v) for v in vols],
      trailing=False, coste_diario_bp=1.5)

# ---------- 5. efecto de la consistencia ----------
for c in [0.20, 0.30]:
    tabla(f"5) SIN VENTAJA · consistencia {c:.0%} · estatico",
          [(f"vol {v:.0%}", 0.0, v) for v in vols],
          trailing=False, consistencia=c)

# ---------- 6. ruina del jugador analitica ----------
print("\n6) COMPROBACION ANALITICA (deriva cero, tiempo infinito, DD estatico)")
print(f"   P(tocar +3.000 antes de -3.500) = 3500/6500 = {3500/6500:.1%}")
print("   La simulacion a 12 meses debe quedar por DEBAJO de esa cifra")
print("   (falta de tiempo) y acercarse a ella al subir la volatilidad.")
