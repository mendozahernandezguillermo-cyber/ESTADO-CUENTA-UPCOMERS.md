#!/usr/bin/env python3
"""
Seleccion de la variante mas rentable en datos recientes.

REGLAS DECLARADAS ANTES DE MIRAR:
  - Solo largos. En 2020-2026 los cortos pierden en las 3 hipotesis.
  - Universo CERRADO de 6 variantes. No se anaden mas despues de ver
    los resultados. 6 pruebas -> correccion de Bonferroni alfa/6.
  - Plano overnight siempre (no se paga swap).
  - El rival a batir NO es cero: es comprar y mantener el CFD, que
    rinde el indice menos 4.56%/ano de swap.
  - Se reporta 2011-2019 aunque la decision sea sobre 2020-2026, para
    que la dependencia de regimen quede a la vista.

Coste: 0.40 bp ida+vuelta (spread 0.70 pts + holgura por slippage).
"""

import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

PRE_INI, PRE_FIN = 8 * 60, 9 * 60 + 29
OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60
MOM_WIN = 15
VOL_LB = 20
COST_BP = 0.40
SWAP_ANUAL = 4.56
N_VARIANTES = 6


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    et = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(fecha=et.dt.date,
                   tod=et.dt.hour * 60 + et.dt.minute,
                   dow=et.dt.dayofweek)
    return df[(df["dow"] < 5) & (df["tod"] >= PRE_INI) & (df["tod"] <= END_MIN)]


def sesiones(df):
    out = []
    prev_close = None
    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        h = g["high"].to_numpy(float)
        l = g["low"].to_numpy(float)
        c = g["close"].to_numpy(float)
        pre = (tod >= PRE_INI) & (tod <= PRE_FIN)
        post = tod >= OPEN_MIN
        if pre.sum() < 30 or post.sum() < 300:
            if post.sum():
                prev_close = c[post][-1]
            continue
        i0 = int(np.argmax(post))
        s = dict(fecha=fecha, dow=int(g["dow"].iloc[0]), tod=tod,
                 o=o, h=h, l=l, c=c, i0=i0,
                 apertura=float(o[i0]),
                 cierre=float(c[post][-1]),
                 pre_hi=float(h[pre].max()),
                 pre_lo=float(l[pre].min()),
                 rango=float(h[post].max() - l[post].min()),
                 prev_close=prev_close)
        s["gap_bp"] = ((s["apertura"] / prev_close - 1) * 1e4
                       if prev_close else None)
        out.append(s)
        prev_close = s["cierre"]

    rangos = [s["rango"] for s in out]
    for k, s in enumerate(out):
        s["vol"] = (float(np.median(rangos[k - VOL_LB:k]))
                    if k >= VOL_LB else None)
    res = [s for s in out if s["vol"] and s["gap_bp"] is not None]
    # retorno del dia anterior, para el filtro de reversion
    for k, s in enumerate(res):
        s["r_prev"] = (res[k - 1]["cierre"] / res[k - 1]["apertura"] - 1) * 1e4 \
            if k > 0 else 0.0
    return res


def bp_open_close(s):
    return (s["cierre"] / s["apertura"] - 1) * 1e4 - COST_BP


def bp_open_mas(s, minutos):
    j = np.where(s["tod"] >= OPEN_MIN + minutos)[0]
    j = int(j[0]) if len(j) else len(s["tod"]) - 1
    return (s["c"][j] / s["apertura"] - 1) * 1e4 - COST_BP


def variantes(ses):
    """Devuelve dict nombre -> lista de (fecha, bp). Solo largos."""
    V = {n: [] for n in ["1_diario_open_close", "2_diario_open_169",
                         "3_solo_gap_bajista", "4_solo_mom_alcista",
                         "5_solo_rompe_prehigh", "6_solo_tras_dia_bajista"]}
    for s in ses:
        f = s["fecha"]
        V["1_diario_open_close"].append((f, bp_open_close(s)))
        V["2_diario_open_169"].append((f, bp_open_mas(s, 169)))

        if s["gap_bp"] < 0:
            V["3_solo_gap_bajista"].append((f, bp_open_close(s)))

        idx = np.where(s["tod"] >= OPEN_MIN + MOM_WIN)[0]
        if len(idx):
            im = int(idx[0])
            if s["o"][im] > s["apertura"]:
                V["4_solo_mom_alcista"].append(
                    (f, (s["cierre"] / s["o"][im] - 1) * 1e4 - COST_BP))

        up = s["pre_hi"] + 0.02 * s["vol"]
        post = s["tod"] >= OPEN_MIN
        hit = np.where(post & (s["h"] >= up))[0]
        if len(hit):
            i = int(hit[0])
            if i + 1 < len(s["tod"]):
                V["5_solo_rompe_prehigh"].append(
                    (f, (s["cierre"] / s["c"][i] - 1) * 1e4 - COST_BP))

        if s["r_prev"] < 0:
            V["6_solo_tras_dia_bajista"].append((f, bp_open_close(s)))
    return V


def metricas(pares, anos):
    if len(pares) < 30:
        return None
    x = np.array([p[1] for p in pares]) / 1e4          # a fraccion
    n = len(x)
    total = np.expm1(np.log1p(x).sum())
    cagr = 100 * ((1 + total) ** (1 / anos) - 1)
    # vol anualizada: n trades repartidos en 'anos'
    vol = 100 * x.std(ddof=1) * np.sqrt(n / anos)
    eq = np.log1p(x).cumsum()
    mdd = 100 * float((np.maximum.accumulate(eq) - eq).max()) if n else 0.0
    t, p2 = stats.ttest_1samp(x, 0.0)
    return dict(n=n, trades_ano=n / anos, cagr=cagr, vol=vol,
                sharpe=cagr / vol if vol else np.nan,
                mdd=mdd, wr=100 * (x > 0).mean(),
                media_bp=1e4 * x.mean(), t=t,
                p=(p2 / 2 if t > 0 else 1 - p2 / 2))


def informe(ses, lo, hi, etiqueta):
    sub = [s for s in ses if lo <= s["fecha"].year <= hi]
    anos = len(sub) / 252.0
    V = variantes(sub)

    # rival: comprar y mantener el CFD (indice - swap)
    r = np.array([np.log(s["cierre"] / s["prev_close"]) for s in sub])
    bh_cagr = 100 * (np.exp(r.sum() / anos) - 1) - SWAP_ANUAL
    bh_vol = 100 * r.std(ddof=1) * np.sqrt(252)
    eq = r.cumsum()
    bh_mdd = 100 * float((np.maximum.accumulate(eq) - eq).max())

    print("\n" + "=" * 92)
    print("  %s   (%d sesiones, %.1f anos)" % (etiqueta, len(sub), anos))
    print("=" * 92)
    print("  RIVAL  comprar y mantener CFD : CAGR %+6.2f%%  vol %5.2f%%  "
          "Sharpe %.3f  maxDD %.1f%%" % (bh_cagr, bh_vol,
                                         bh_cagr / bh_vol, bh_mdd))
    print()
    print("  %-26s %5s %6s %8s %7s %7s %7s %6s %6s %7s"
          % ("variante", "n", "op/ano", "CAGR", "vol", "Sharpe",
             "maxDD", "wr%", "t", "p_bonf"))
    print("  " + "-" * 88)

    filas = []
    for nom in sorted(V):
        mt = metricas(V[nom], anos)
        if not mt:
            continue
        pb = min(1.0, mt["p"] * N_VARIANTES)
        filas.append((nom, mt, pb))
        print("  %-26s %5d %6.0f %+7.2f%% %6.2f%% %7.3f %6.1f%% %6.2f "
              "%+5.2f %7.4f"
              % (nom, mt["n"], mt["trades_ano"], mt["cagr"], mt["vol"],
                 mt["sharpe"], mt["mdd"], mt["wr"], mt["t"], pb))

    print()
    mejor = max(filas, key=lambda z: z[1]["sharpe"])
    print("  Mejor por Sharpe: %s (%.3f)  vs rival %.3f  -> %s"
          % (mejor[0], mejor[1]["sharpe"], bh_cagr / bh_vol,
             "BATE al rival" if mejor[1]["sharpe"] > bh_cagr / bh_vol
             else "NO bate al rival"))
    return filas, bh_cagr / bh_vol


def main():
    ses = sesiones(cargar())
    print("Sesiones: %d  (%s -> %s)"
          % (len(ses), ses[0]["fecha"], ses[-1]["fecha"]))

    informe(ses, 2011, 2019, "CONTRASTE  2011-2019 (no decide)")
    filas, bh = informe(ses, 2020, 2026, "DECISION  2020-2026 (datos recientes)")
    informe(ses, 2023, 2026, "SUBVENTANA  2023-2026 (robustez)")


if __name__ == "__main__":
    main()
