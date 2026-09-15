"""
Calculo DEFINITIVO de la Opcion B para THL.

- Serie mensual de THL: transcrita de la web y VERIFICADA (los 5 totales anuales
  y el total compuesto de 36.00% cuadran exactamente).
- Benchmark: S&P 500 (^GSPC) mensual real, descargado de Yahoo Finance.
- Calcula: vol, Sharpe, correlacion REAL, umbral de Markowitz, pesos optimos
  y mejora del Sharpe de cartera.

Criterio:  anadir S a B mejora el Sharpe  <=>  SR_S > rho(S,B) * SR_B
"""

import datetime
import json
import urllib.request

import numpy as np

RISK_FREE = 4.0  # % anual

# ---------------------------------------------------------------------------
# THL — retornos mensuales (%) desde Julio 2022 hasta Agosto 2026 (50 meses).
# VERIFICADO: totales anuales 0.17 / 8.98 / 8.10 / 9.33 / 5.41  ->  compuesto 36.01%
# ---------------------------------------------------------------------------
THL = {
    2022: [None, None, None, None, None, None, 0.00, 3.76, -1.67, -3.73, 1.13, 0.85],
    2023: [0.53, 2.22, 0.33, 0.06, 2.27, 1.34, -1.48, 2.07, -1.49, 1.36, 1.49, 0.03],
    2024: [2.06, 1.21, -1.96, -3.36, 2.15, 0.82, 4.63, -0.09, -0.81, -3.04, 3.28, 3.30],
    2025: [2.33, -2.02, 1.77, -0.68, -3.29, 0.03, 2.55, -0.25, 2.81, 6.39, 0.46, -0.78],
    2026: [-0.78, -0.52, 0.35, 4.68, 1.29, -1.33, -0.12, 1.83, None, None, None, None],
}

YAHOO = (
    "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
    "?interval=1mo&period1=1654041600&period2=1788220800"
)


def thl_series():
    """Devuelve [(YYYY-MM, retorno_pct), ...] ordenado."""
    out = []
    for year in sorted(THL):
        for i, v in enumerate(THL[year], start=1):
            if v is not None:
                out.append((f"{year}-{i:02d}", v))
    return out


def spx_monthly_returns():
    """Descarga ^GSPC mensual y devuelve {'YYYY-MM': retorno_pct}."""
    req = urllib.request.Request(YAHOO, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        data = json.load(fh)

    res = data["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["adjclose"][0]["adjclose"]

    # Un cierre por mes: nos quedamos con el ultimo dato de cada mes
    by_month = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        key = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m")
        by_month[key] = c

    months = sorted(by_month)
    rets = {}
    for prev, cur in zip(months, months[1:]):
        rets[cur] = (by_month[cur] / by_month[prev] - 1) * 100
    return rets


def stats(r_pct, official_total=None):
    r = np.array(r_pct) / 100.0
    n = len(r)
    years = n / 12.0
    total = official_total / 100.0 if official_total is not None else np.prod(1 + r) - 1
    cagr = (1 + total) ** (1 / years) - 1
    vol_a = r.std(ddof=1) * np.sqrt(12)

    eq = np.cumprod(1 + r)
    mdd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()

    return {
        "n": n,
        "cagr": cagr * 100,
        "vol": vol_a * 100,
        "mdd": mdd * 100,
        "sharpe": (cagr * 100 - RISK_FREE) / (vol_a * 100),
    }


def combined_sharpe(sr_b, sr_s, rho):
    return np.sqrt((sr_b**2 + sr_s**2 - 2 * rho * sr_b * sr_s) / (1 - rho**2))


def tangency(mu_b, mu_s, sig_b, sig_s, rho):
    cov = rho * sig_b * sig_s
    w = np.linalg.solve(np.array([[sig_b**2, cov], [cov, sig_s**2]]),
                        np.array([mu_b, mu_s]))
    return w / w.sum()


def main():
    thl = thl_series()
    spx = spx_monthly_returns()

    pairs = [(m, v, spx[m]) for m, v in thl if m in spx]
    months = [p[0] for p in pairs]
    a_thl = np.array([p[1] for p in pairs])
    a_spx = np.array([p[2] for p in pairs])

    print("=" * 70)
    print(f"Meses solapados: {len(pairs)}   ({months[0]} .. {months[-1]})")
    print("=" * 70)

    s_thl = stats(a_thl, official_total=36.00)
    s_spx = stats(a_spx)

    print(f"{'':<22}{'THL':>14}{'S&P 500':>14}")
    print("-" * 70)
    for label, key, suf in [
        ("CAGR", "cagr", "%"),
        ("Vol anualizada", "vol", "%"),
        ("Max drawdown (mens.)", "mdd", "%"),
        ("SHARPE", "sharpe", ""),
    ]:
        print(f"{label:<22}{s_thl[key]:>13.2f}{suf}{s_spx[key]:>13.2f}{suf}")

    rho = float(np.corrcoef(a_thl, a_spx)[0, 1])
    rho_max = s_thl["sharpe"] / s_spx["sharpe"]

    print()
    print("=" * 70)
    print("CRITERIO OPCION B")
    print("=" * 70)
    print(f"  Correlacion REAL THL vs S&P 500 .......  rho = {rho:+.3f}")
    print(f"  Umbral maximo tolerable ..............  rho_max = {rho_max:.3f}")
    print()

    ok = s_thl["sharpe"] > rho * s_spx["sharpe"]
    print(f"  SR_THL = {s_thl['sharpe']:.3f}   vs   rho * SR_S&P = {rho * s_spx['sharpe']:.3f}")
    print()
    print(f"  >>> VEREDICTO: {'PASA — mejora la cartera' if ok else 'NO PASA'}")

    mu_b, mu_s = s_spx["cagr"] - RISK_FREE, s_thl["cagr"] - RISK_FREE
    w = tangency(mu_b, mu_s, s_spx["vol"], s_thl["vol"], rho)
    sr_c = combined_sharpe(s_spx["sharpe"], s_thl["sharpe"], rho)

    print()
    print("=" * 70)
    print("CARTERA OPTIMA (S&P 500 + THL)")
    print("=" * 70)
    print(f"  Peso S&P 500 ......  {w[0]*100:6.1f} %")
    print(f"  Peso THL ..........  {w[1]*100:6.1f} %")
    print()
    print(f"  Sharpe solo S&P ...  {s_spx['sharpe']:.3f}")
    print(f"  Sharpe cartera ....  {sr_c:.3f}")
    print(f"  MEJORA ............  {(sr_c/s_spx['sharpe']-1)*100:+.1f} %")

    # Comportamiento en los peores meses del S&P
    print()
    print("=" * 70)
    print("Los 6 peores meses del S&P 500 — que hizo THL")
    print("=" * 70)
    idx = np.argsort(a_spx)[:6]
    print(f"  {'Mes':<10}{'S&P':>10}{'THL':>10}")
    print("  " + "-" * 30)
    for i in sorted(idx, key=lambda j: months[j]):
        print(f"  {months[i]:<10}{a_spx[i]:>9.2f}%{a_thl[i]:>9.2f}%")
    print()
    print(f"  Media S&P en esos meses: {a_spx[idx].mean():+.2f}%")
    print(f"  Media THL en esos meses: {a_thl[idx].mean():+.2f}%")


if __name__ == "__main__":
    main()
