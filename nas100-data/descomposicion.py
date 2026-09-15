#!/usr/bin/env python3
"""
Descomposicion nocturno / intradia del NASDAQ 100, 2011-2026.

Pregunta que responde: la opcion A propone un EA plano overnight. Eso
renuncia por construccion al tramo nocturno del retorno del indice.
Antes de construir nada hay que saber cuanto retorno vive en cada
tramo y como se correlacionan entre si.

  retorno nocturno  = cierre 16:00 -> apertura 09:30 siguiente
  retorno intradia  = apertura 09:30 -> cierre 16:00 del mismo dia

Si el retorno del indice vive sobre todo en el tramo nocturno, un EA
plano overnight parte con viento en contra en el lado largo, pero
tambien queda estructuralmente descorrelacionado del indice. Eso seria
la explicacion mecanica de la rho=0.125 de THL.
"""

import glob
import os
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60


def cargar_diario():
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
    df = df[df["dow"] < 5]

    filas = []
    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        dentro = (tod >= OPEN_MIN) & (tod <= END_MIN)
        if dentro.sum() < 300:      # descarta medios dias y festivos
            continue
        filas.append(dict(fecha=fecha,
                          apertura=float(o[dentro][0]),
                          cierre=float(c[dentro][-1])))

    d = pd.DataFrame(filas)
    d["cierre_prev"] = d["cierre"].shift(1)
    d = d.dropna().reset_index(drop=True)

    d["r_noct"] = np.log(d["apertura"] / d["cierre_prev"])
    d["r_intra"] = np.log(d["cierre"] / d["apertura"])
    d["r_total"] = np.log(d["cierre"] / d["cierre_prev"])
    return d


def sharpe(x, per=252):
    if x.std() == 0:
        return np.nan
    return np.sqrt(per) * x.mean() / x.std()


def bloque(d, nom):
    n = len(d)
    tn, ti, tt = d["r_noct"].sum(), d["r_intra"].sum(), d["r_total"].sum()
    print("\n--- %s  (%d sesiones, %s -> %s) ---"
          % (nom, n, d["fecha"].iloc[0], d["fecha"].iloc[-1]))
    anos = n / 252.0
    print("  %-22s %10s %10s %10s" % ("", "NOCTURNO", "INTRADIA", "TOTAL"))
    print("  %-22s %+9.1f%% %+9.1f%% %+9.1f%%"
          % ("retorno acumulado", 100 * (np.exp(tn) - 1),
             100 * (np.exp(ti) - 1), 100 * (np.exp(tt) - 1)))
    print("  %-22s %+9.2f%% %+9.2f%% %+9.2f%%"
          % ("CAGR", 100 * (np.exp(tn / anos) - 1),
             100 * (np.exp(ti / anos) - 1), 100 * (np.exp(tt / anos) - 1)))
    print("  %-22s %9.2f%% %9.2f%% %9.2f%%"
          % ("vol anualizada", 100 * d["r_noct"].std() * np.sqrt(252),
             100 * d["r_intra"].std() * np.sqrt(252),
             100 * d["r_total"].std() * np.sqrt(252)))
    print("  %-22s %9.2f %10.2f %10.2f"
          % ("Sharpe (rf=0)", sharpe(d["r_noct"]), sharpe(d["r_intra"]),
             sharpe(d["r_total"])))
    print("  %-22s %+9.2f %10s %10s"
          % ("cuota del total", 100 * tn / tt if tt else np.nan,
             "%+.2f" % (100 * ti / tt) if tt else "-", "100.00"))
    print("  correlaciones diarias:")
    print("    nocturno vs intradia : %+.4f" % d["r_noct"].corr(d["r_intra"]))
    print("    intradia vs total    : %+.4f" % d["r_intra"].corr(d["r_total"]))
    print("    nocturno vs total    : %+.4f" % d["r_noct"].corr(d["r_total"]))


def mensual(d):
    d = d.copy()
    d["mes"] = pd.to_datetime(d["fecha"]).dt.to_period("M")
    m = d.groupby("mes")[["r_noct", "r_intra", "r_total"]].sum()
    print("\n--- CORRELACIONES MENSUALES (lo que importa para cartera) ---")
    print("  intradia vs total : %+.4f" % m["r_intra"].corr(m["r_total"]))
    print("  nocturno vs total : %+.4f" % m["r_noct"].corr(m["r_total"]))
    print("  intradia vs nocturno: %+.4f" % m["r_intra"].corr(m["r_noct"]))
    print("  n meses: %d" % len(m))

    # criterio de Markowitz aplicado al tramo intradia como estrategia
    sr_i = np.sqrt(12) * m["r_intra"].mean() / m["r_intra"].std()
    sr_t = np.sqrt(12) * m["r_total"].mean() / m["r_total"].std()
    rho = m["r_intra"].corr(m["r_total"])
    print("\n  Sharpe mensual->anual  intradia=%.3f  indice=%.3f  rho=%.3f"
          % (sr_i, sr_t, rho))
    print("  umbral Markowitz: se necesita SR_intra > rho*SR_indice = %.3f"
          % (rho * sr_t))
    print("  -> %s" % ("PASA" if sr_i > rho * sr_t else "NO PASA"))
    return m


def main():
    d = cargar_diario()
    print("Sesiones diarias construidas: %d" % len(d))

    bloque(d, "MUESTRA COMPLETA 2011-2026")
    bloque(d[pd.to_datetime(d["fecha"]).dt.year < 2020], "2011-2019")
    bloque(d[pd.to_datetime(d["fecha"]).dt.year >= 2020], "2020-2026")

    m = mensual(d)

    out = os.path.join(os.path.dirname(RAW), "diario.csv")
    d.to_csv(out, index=False)
    print("\nSerie diaria en diario.csv (%d filas)" % len(d))


if __name__ == "__main__":
    main()
