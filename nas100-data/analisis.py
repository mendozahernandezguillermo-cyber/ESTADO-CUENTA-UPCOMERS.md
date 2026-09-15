#!/usr/bin/env python3
"""
Banco de pruebas de disparadores sobre NASDAQ 100 cash, 15 anos.
Fuente: Dukascopy USATECH.IDX/USD, M1, 2011-09 -> 2026-08.

Dos correcciones frente a la version MQL5 (que solo tenia 7 meses):

  1. TODO NORMALIZADO POR VOLATILIDAD. El NDX pasa de 2.200 (2011) a
     29.000 (2026). Un umbral de "15 puntos" significa cosas
     completamente distintas en cada extremo de la muestra. Aqui los
     umbrales y los TP/SL se expresan como fraccion del rango tipico
     de sesion (mediana de las 20 sesiones previas), y los resultados
     en puntos basicos del indice. Asi son comparables en 15 anos.

  2. SEPARACION LARGOS / CORTOS. El NDX multiplico por 13 en el
     periodo. Cualquier estrategia con sesgo largo neto parece
     rentable. Sin separar, no se distingue edge de deriva.

Disciplina de muestra: descubrimiento 2011-2019, validacion 2020-2026.
La validacion se mira UNA vez, al final.
"""

import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

# ventanas en minutos desde medianoche, hora de NUEVA YORK
PRE_INI, PRE_FIN = 8 * 60, 9 * 60 + 29     # 08:00 - 09:29 premercado
OPEN_MIN = 9 * 60 + 30                     # 09:30 apertura cash
END_MIN = 16 * 60                          # 16:00 cierre cash
MAX_MIN = 169                              # salida por tiempo (media de THL)

MOM_WIN = 15                               # H2: minutos de momentum
VOL_LOOKBACK = 20                          # sesiones para la unidad de vol

# coste ida+vuelta en puntos basicos del indice.
# 0.70 pts sobre 29.060 = 0.24 bp. Proporcional, no absoluto.
COST_BP = 0.24

SPLIT = pd.Timestamp("2020-01-01").date()  # descubrimiento | validacion

# escalera de TP/SL en fracciones de la unidad de volatilidad.
# 0 = sin TP ni SL, salida pura por tiempo.
LADDER = [0.0, 0.25, 0.50, 0.75, 1.00, 1.50]


# --------------------------------------------------------------------
def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    if not files:
        raise SystemExit("No hay CSVs en %s" % RAW)
    print("Ficheros: %d" % len(files))

    partes = []
    for f in files:
        d = pd.read_csv(f, usecols=["timestamp", "open", "high", "low", "close"])
        partes.append(d)
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")

    dt = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    et = dt.dt.tz_convert("America/New_York")

    df = df.assign(
        fecha=et.dt.date,
        tod=et.dt.hour * 60 + et.dt.minute,
        dow=et.dt.dayofweek,
    )
    # solo dias laborables y la ventana que nos interesa
    df = df[(df["dow"] < 5) & (df["tod"] >= PRE_INI) & (df["tod"] <= END_MIN)]
    print("Velas M1 utiles: %d" % len(df))
    print("Rango: %s -> %s" % (df["fecha"].iloc[0], df["fecha"].iloc[-1]))
    return df


# --------------------------------------------------------------------
def construir_sesiones(df):
    ses = []
    prev_close = None

    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        h = g["high"].to_numpy(float)
        l = g["low"].to_numpy(float)
        c = g["close"].to_numpy(float)

        pre = (tod >= PRE_INI) & (tod <= PRE_FIN)
        post = tod >= OPEN_MIN
        if pre.sum() < 30 or post.sum() < 120:
            # sesion incompleta o medio dia festivo
            if post.sum() > 0:
                prev_close = c[post][-1]
            continue

        i_open = int(np.argmax(post))          # primera vela >= 09:30
        s = dict(
            fecha=fecha,
            dow=int(g["dow"].iloc[0]),
            tod=tod, o=o, h=h, l=l, c=c,
            i_open=i_open,
            open_px=float(o[i_open]),
            pre_hi=float(h[pre].max()),
            pre_lo=float(l[pre].min()),
            sess_hi=float(h[post].max()),
            sess_lo=float(l[post].min()),
            sess_close=float(c[post][-1]),
            prev_close=prev_close,
        )
        s["rango_sesion"] = s["sess_hi"] - s["sess_lo"]
        s["rango_pre"] = s["pre_hi"] - s["pre_lo"]
        s["gap"] = (s["open_px"] - prev_close) if prev_close else None
        ses.append(s)
        prev_close = s["sess_close"]

    # unidad de volatilidad: mediana del rango de las 20 sesiones previas
    rangos = [s["rango_sesion"] for s in ses]
    for k, s in enumerate(ses):
        if k < VOL_LOOKBACK:
            s["vol_unit"] = None
        else:
            s["vol_unit"] = float(np.median(rangos[k - VOL_LOOKBACK:k]))

    ses = [s for s in ses if s["vol_unit"] and s["gap"] is not None]
    print("Sesiones utiles: %d" % len(ses))
    return ses


# --------------------------------------------------------------------
def simular(s, i_entry, direc, entry_px, tp_pts, sl_pts):
    """Devuelve (bp_neto, dur_min, motivo, ambiguo).
    tp_pts <= 0 -> sin TP ni SL, solo salida por tiempo."""
    tod, h, l, c = s["tod"], s["h"], s["l"], s["c"]
    n = len(tod)
    t0 = tod[i_entry]
    usa_ts = tp_pts > 0

    tp = entry_px + tp_pts * direc
    sl = entry_px - sl_pts * direc

    for i in range(i_entry, n):
        if usa_ts:
            if direc > 0:
                hit_sl, hit_tp = l[i] <= sl, h[i] >= tp
            else:
                hit_sl, hit_tp = h[i] >= sl, l[i] <= tp
            if hit_sl and hit_tp:
                bp = (-sl_pts / entry_px) * 1e4 - COST_BP
                return bp, int(tod[i] - t0), "SL", True
            if hit_sl:
                bp = (-sl_pts / entry_px) * 1e4 - COST_BP
                return bp, int(tod[i] - t0), "SL", False
            if hit_tp:
                bp = (tp_pts / entry_px) * 1e4 - COST_BP
                return bp, int(tod[i] - t0), "TP", False

        if tod[i] >= END_MIN or (tod[i] - t0) >= MAX_MIN:
            bruto = (c[i] - entry_px) * direc
            return (bruto / entry_px) * 1e4 - COST_BP, int(tod[i] - t0), \
                   ("CIERRE" if tod[i] >= END_MIN else "TIEMPO"), False

    bruto = (c[-1] - entry_px) * direc
    return (bruto / entry_px) * 1e4 - COST_BP, int(tod[-1] - t0), "FIN", False


# --------------------------------------------------------------------
def correr(ses, nivel):
    """nivel = fraccion de vol_unit para TP/SL. 0 = solo tiempo."""
    out = []
    for s in ses:
        vu = s["vol_unit"]
        tp = sl = nivel * vu
        tod, o, h, l = s["tod"], s["o"], s["h"], s["l"]
        i_open, n = s["i_open"], len(tod)

        # ---- H1: ruptura del rango premercado -----------------------
        buf = 0.02 * vu
        up, dn = s["pre_hi"] + buf, s["pre_lo"] - buf
        for i in range(i_open, n):
            if tod[i] >= END_MIN - MAX_MIN:
                break
            d = 0
            if h[i] >= up:
                d = 1
            elif l[i] <= dn:
                d = -1
            if d and i + 1 < n:
                bp, dur, mot, amb = simular(s, i + 1, d, s["c"][i], tp, sl)
                out.append((1, s["fecha"], d, bp, dur, mot, amb))
                break

        # ---- H2: momentum de los primeros MOM_WIN minutos -----------
        idx = np.where(tod >= OPEN_MIN + MOM_WIN)[0]
        if len(idx):
            im = int(idx[0])
            push = o[im] - s["open_px"]
            if abs(push) >= 0.10 * vu:
                d = 1 if push > 0 else -1
                bp, dur, mot, amb = simular(s, im, d, o[im], tp, sl)
                out.append((2, s["fecha"], d, bp, dur, mot, amb))

        # ---- H3: reversion del gap ----------------------------------
        if abs(s["gap"]) >= 0.10 * vu:
            d = -1 if s["gap"] > 0 else 1
            bp, dur, mot, amb = simular(s, i_open, d, s["open_px"], tp, sl)
            out.append((3, s["fecha"], d, bp, dur, mot, amb))

    return pd.DataFrame(out, columns=["hip", "fecha", "dir", "bp",
                                      "dur", "motivo", "amb"])


# --------------------------------------------------------------------
def stats_bloque(x):
    n = len(x)
    if n < 10:
        return dict(n=n, wr=np.nan, media=np.nan, t=np.nan, p=np.nan)
    t, p2 = stats.ttest_1samp(x, 0.0)
    return dict(n=n, wr=100.0 * (x > 0).mean(), media=x.mean(),
                sd=x.std(ddof=1), t=t, p=p2 / 2 if t > 0 else 1 - p2 / 2)


def informe(tr, ses, etiqueta):
    print("\n" + "=" * 78)
    print("  %s" % etiqueta)
    print("=" * 78)

    # deriva de referencia: comprar en la apertura y soltar 169 min
    drift = []
    for s in ses:
        i = s["i_open"]
        j = np.where(s["tod"] >= s["tod"][i] + MAX_MIN)[0]
        j = int(j[0]) if len(j) else len(s["tod"]) - 1
        drift.append((s["c"][j] - s["open_px"]) / s["open_px"] * 1e4)
    d = stats_bloque(np.array(drift))
    print("\nDERIVA (comprar en apertura, soltar a 169 min, sin coste):")
    print("  n=%d  media=%+.2f bp  t=%.2f  p=%.4f" %
          (d["n"], d["media"], d["t"], d["p"]))
    print("  -> cualquier hipotesis con sesgo largo hereda esto\n")

    hdr = ("hip nivel     n    wr%%   media_bp    sd     t      p     "
           "dur  amb  n_lar  bp_lar  n_cor  bp_cor")
    print(hdr)
    print("-" * len(hdr))

    for niv in LADDER:
        sub_all = tr[tr["nivel"] == niv]
        for hip in (1, 2, 3):
            x = sub_all[sub_all["hip"] == hip]
            if len(x) < 10:
                continue
            a = stats_bloque(x["bp"].to_numpy())
            lar = x[x["dir"] == 1]["bp"]
            cor = x[x["dir"] == -1]["bp"]
            print("%3d %5.2f %5d %6.2f %+9.2f %6.1f %+6.2f %6.4f %5.0f %4d "
                  "%6d %+7.2f %6d %+7.2f" %
                  (hip, niv, a["n"], a["wr"], a["media"], a["sd"], a["t"],
                   a["p"], x["dur"].mean(), int(x["amb"].sum()),
                   len(lar), lar.mean() if len(lar) else 0,
                   len(cor), cor.mean() if len(cor) else 0))
        print()


# --------------------------------------------------------------------
def main():
    df = cargar()
    ses = construir_sesiones(df)

    partes = []
    for niv in LADDER:
        t = correr(ses, niv)
        t["nivel"] = niv
        partes.append(t)
    tr = pd.concat(partes, ignore_index=True)

    ses_is = [s for s in ses if s["fecha"] < SPLIT]
    ses_oos = [s for s in ses if s["fecha"] >= SPLIT]
    tr_is = tr[tr["fecha"] < SPLIT]
    tr_oos = tr[tr["fecha"] >= SPLIT]

    informe(tr_is, ses_is, "DESCUBRIMIENTO  2011-09 -> 2019-12  (%d sesiones)"
            % len(ses_is))
    informe(tr_oos, ses_oos, "VALIDACION  2020-01 -> 2026-08  (%d sesiones)"
            % len(ses_oos))

    tr.to_csv(os.path.join(os.path.dirname(RAW), "trades.csv"), index=False)
    print("\nDetalle en trades.csv (%d filas)" % len(tr))

    # umbral de deteccion segun tamano de muestra
    print("\nPotencia: con n trades y 18 celdas probadas, el acierto")
    print("minimo detectable (alfa=0.05 corregido) es:")
    for n in (155, 500, 1000, 2000, 3500):
        se = 0.5 / np.sqrt(n)
        print("  n=%5d  ->  %.1f%%" % (n, 50 + 2.45 * se * 100))


if __name__ == "__main__":
    main()
