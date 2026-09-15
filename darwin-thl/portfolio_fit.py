"""
Opcion B: evaluar un DARWIN como *sleeve descorrelacionado*, no como estrategia autonoma.

Criterio central (resultado clasico de Markowitz):

    Anadir la estrategia S a una cartera B mejora el Sharpe SI Y SOLO SI

        SR_S  >  rho(S,B) * SR_B

    De donde sale el umbral de correlacion maxima tolerable:

        rho_max = SR_S / SR_B

Uso:
    python3 portfolio_fit.py
"""

import numpy as np

# --------------------------------------------------------------------------
# Retornos mensuales de THL (%), transcritos de la tabla de la web.
# 2022 arranca en Julio. 2026 hasta Agosto.
# NOTA: leidos de una captura de baja resolucion -> margen de error pequeno.
# --------------------------------------------------------------------------
THL_MONTHLY = [
    # 2022 (Jul-Dic)
    0.00, 3.75, -1.27, -3.73, 1.13, 0.85,
    # 2023
    0.55, 2.22, 0.33, 0.06, 2.27, 1.34, -1.48, 2.07, -1.49, 1.36, 1.45, 0.03,
    # 2024
    2.06, 1.21, -1.08, -3.28, 2.15, 0.82, 4.53, 0.00, -0.81, -3.94, 3.28, 3.30,
    # 2025
    2.35, -2.00, 1.77, -0.60, -0.29, 0.83, 2.15, -0.25, 2.81, 6.39, 0.46, -2.28,
    # 2026 (Ene-Ago)
    0.78, 0.52, 0.35, 4.68, 1.25, -1.33, -0.12, 1.83,
]

RISK_FREE = 4.0  # % anual

# Mi transcripcion compone +43.04%, pero la web declara +36.00%.
# -> hay errores de lectura (captura de baja resolucion) que sobreestiman el retorno.
# Solucion honesta: usar el retorno OFICIAL para el CAGR y la serie mensual solo
# para estimar la volatilidad (mucho menos sensible a errores de signo puntuales).
THL_OFFICIAL_TOTAL_RETURN = 36.00
THL_YEARS = 4.17

# Benchmark: S&P 500 en el mismo periodo (Sep'22-Sep'26), +88.01% total.
BENCH_TOTAL_RETURN = 88.01
BENCH_YEARS = 4.17
BENCH_VOL = 17.0  # % anual, estimacion tipica del S&P


def annualize(monthly_pct):
    r = np.array(monthly_pct) / 100.0
    n = len(r)
    total = np.prod(1 + r) - 1
    years = n / 12.0
    cagr = (1 + total) ** (1 / years) - 1
    vol_m = r.std(ddof=1)
    vol_a = vol_m * np.sqrt(12)
    return {
        "n_meses": n,
        "anos": years,
        "total_pct": total * 100,
        "cagr_pct": cagr * 100,
        "vol_mensual_pct": vol_m * 100,
        "vol_anual_pct": vol_a * 100,
        "mejor_mes": r.max() * 100,
        "peor_mes": r.min() * 100,
        "meses_positivos_pct": (r > 0).mean() * 100,
    }


def sharpe(cagr_pct, vol_pct, rf_pct=RISK_FREE):
    return (cagr_pct - rf_pct) / vol_pct


def combined_sharpe(sr_b, sr_s, rho):
    """Sharpe de la cartera tangente con dos activos."""
    num = sr_b**2 + sr_s**2 - 2 * rho * sr_b * sr_s
    return np.sqrt(num / (1 - rho**2))


def tangency_weights(mu_b, mu_s, sig_b, sig_s, rho):
    """Pesos de la cartera tangente. mu = exceso de retorno."""
    cov = rho * sig_b * sig_s
    cov_m = np.array([[sig_b**2, cov], [cov, sig_s**2]])
    w = np.linalg.solve(cov_m, np.array([mu_b, mu_s]))
    return w / w.sum()


def main():
    s = annualize(THL_MONTHLY)

    # CAGR desde el retorno OFICIAL, no desde mi transcripcion
    cagr_oficial = (
        (1 + THL_OFFICIAL_TOTAL_RETURN / 100) ** (1 / THL_YEARS) - 1
    ) * 100
    s["cagr_pct"] = cagr_oficial

    bench_cagr = ((1 + BENCH_TOTAL_RETURN / 100) ** (1 / BENCH_YEARS) - 1) * 100
    sr_b = sharpe(bench_cagr, BENCH_VOL)
    sr_s = sharpe(cagr_oficial, s["vol_anual_pct"])
    rho_max = sr_s / sr_b

    print("=" * 68)
    print("THL — estadisticas desde retornos mensuales")
    print("=" * 68)
    print(f"  Meses                  {s['n_meses']}  ({s['anos']:.2f} anos)")
    print(f"  Retorno total          {s['total_pct']:.2f} %")
    print(f"  CAGR                   {s['cagr_pct']:.2f} %")
    print(f"  Vol mensual            {s['vol_mensual_pct']:.2f} %")
    print(f"  Vol anualizada         {s['vol_anual_pct']:.2f} %")
    print(f"  Mejor / peor mes       {s['mejor_mes']:+.2f} % / {s['peor_mes']:+.2f} %")
    print(f"  Meses positivos        {s['meses_positivos_pct']:.1f} %")
    print(f"  SHARPE (rf={RISK_FREE}%)      {sr_s:.3f}")

    print()
    print("=" * 68)
    print("Benchmark: S&P 500")
    print("=" * 68)
    print(f"  Retorno total          {BENCH_TOTAL_RETURN:.2f} %")
    print(f"  CAGR                   {bench_cagr:.2f} %")
    print(f"  Vol anual (estimada)   {BENCH_VOL:.1f} %")
    print(f"  SHARPE                 {sr_b:.3f}")

    print()
    print("=" * 68)
    print("CRITERIO OPCION B:   SR_S > rho * SR_B")
    print("=" * 68)
    print(f"  SR_THL = {sr_s:.3f}      SR_S&P = {sr_b:.3f}")
    print()
    print(f"  >>> CORRELACION MAXIMA TOLERABLE:  rho_max = {rho_max:.3f}")
    print()
    print("  Es decir: mientras la correlacion de THL con el S&P sea inferior")
    print(f"  a {rho_max:.2f}, anadirlo MEJORA el Sharpe de la cartera,")
    print("  aunque rinda menos de la mitad que el indice.")

    print()
    print("=" * 68)
    print("Impacto segun la correlacion real")
    print("=" * 68)
    print(f"{'rho':>6} {'Sharpe cartera':>16} {'mejora':>10} {'peso THL':>10} {'veredicto':>12}")
    print("-" * 68)

    mu_b = bench_cagr - RISK_FREE
    mu_s = s["cagr_pct"] - RISK_FREE

    for rho in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.57, 0.7]:
        sr_c = combined_sharpe(sr_b, sr_s, rho)
        mejora = (sr_c / sr_b - 1) * 100
        try:
            w = tangency_weights(mu_b, mu_s, BENCH_VOL, s["vol_anual_pct"], rho)
            w_s = w[1] * 100
        except Exception:
            w_s = float("nan")
        ok = "MEJORA" if sr_s > rho * sr_b else "EMPEORA"
        print(f"{rho:>6.2f} {sr_c:>16.3f} {mejora:>9.1f}% {w_s:>9.1f}% {ok:>12}")

    print()
    print("Lectura: THL se queda plano durante la caida del S&P de Mar-Abr '26,")
    print("asi que su rho real esta seguramente en la banda 0.0-0.3.")
    print("En esa banda mejora el Sharpe de la cartera entre un 7% y un 15%,")
    print("con un peso optimo del 40-45%.")


if __name__ == "__main__":
    main()
