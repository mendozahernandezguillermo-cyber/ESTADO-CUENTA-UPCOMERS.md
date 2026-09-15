#!/usr/bin/env python3
"""
ANALISIS FORENSE: que condicion de precio se cumplia en los minutos en
que joxemi entro, y no se cumplia en los minutos en que no entro.

DISENO. Cada entrada real se compara con un CONTROL EMPAREJADO POR HORA
DEL DIA: los mismos minutos de reloj en otros dias. Eso elimina por
construccion cualquier efecto de hora del dia, que ya sabemos que no
explica nada (la prueba de las 11:30 dio t=0.31).

Asi, cualquier diferencia entre entradas y controles es la CONDICION DE
PRECIO, no el horario.

La pregunta que discrimina de verdad:
  sus LARGOS siguen a subidas (momentum) o a bajadas (reversion)?
Con 597 largos y 339 cortos, esa pregunta esta bien alimentada.

LIMITACION: el precio es el indice cash de Dukascopy; el opera el CFD
"NASDAQ 100 (Mini)" de Darwinex, derivado del futuro. Para rasgos
DIRECCIONALES (subia o bajaba) las dos series deberian coincidir la
mayor parte del tiempo, pero no es garantia.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = "/projects/sandbox/nas100-data/raw"
ENTRADAS = "entradas_nasdaq.csv"


def cargar_precio():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    ny = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(ny=ny, fecha=ny.dt.date,
                   tod=ny.dt.hour * 60 + ny.dt.minute,
                   dow=ny.dt.dayofweek)
    return df[df["dow"] < 5].reset_index(drop=True)


def indexar(df):
    """dict (fecha) -> (tod array, open array, high, low, close)"""
    idx = {}
    for fecha, g in df.groupby("fecha", sort=True):
        idx[fecha] = (g["tod"].to_numpy(),
                      g["open"].to_numpy(float),
                      g["high"].to_numpy(float),
                      g["low"].to_numpy(float),
                      g["close"].to_numpy(float))
    return idx


def rasgos(idx, fecha, tod):
    """Contexto de precio en (fecha, minuto). None si no hay datos."""
    if fecha not in idx:
        return None
    T, O, H, L, C = idx[fecha]
    j = np.searchsorted(T, tod)
    if j >= len(T) or abs(int(T[j]) - tod) > 5 or j < 60:
        return None
    px = O[j]
    if px <= 0:
        return None

    def ret(n):
        k = j - n
        return (px / O[k] - 1) * 1e4 if k >= 0 and O[k] > 0 else np.nan

    # rango del dia hasta ese momento
    hi = H[:j + 1].max()
    lo = L[:j + 1].min()
    rng = hi - lo
    pos = (px - lo) / rng if rng > 0 else np.nan

    # volatilidad realizada de los 30 min previos
    if j >= 30:
        r = np.diff(np.log(O[j - 30:j + 1]))
        vol30 = float(np.std(r) * 1e4)
    else:
        vol30 = np.nan

    return dict(r5=ret(5), r15=ret(15), r30=ret(30), r60=ret(60),
                r120=ret(120), pos_rango=pos, rango_bp=1e4 * rng / px,
                vol30=vol30, dist_hi=1e4 * (hi - px) / px,
                dist_lo=1e4 * (px - lo) / px)


def main():
    pr = cargar_precio()
    idx = indexar(pr)
    fechas = sorted(idx.keys())
    print("Dias de precio: %d" % len(fechas))

    e = pd.read_csv(ENTRADAS)
    e["ts"] = pd.to_datetime(e["ts"], utc=True, format="ISO8601")
    e["ny"] = e["ts"].dt.tz_convert("America/New_York")
    e["fecha"] = e["ny"].dt.date
    e["tod"] = e["ny"].dt.hour * 60 + e["ny"].dt.minute
    e = e[e["nas"].isin([1.0, -1.0])]
    print("Entradas de NASDAQ con direccion: %d" % len(e))

    rng = np.random.default_rng(20260829)
    fset = set(fechas)

    filas = []
    for _, r in e.iterrows():
        f = rasgos(idx, r["fecha"], int(r["tod"]))
        if f is None:
            continue
        f.update(tipo="ENTRADA", dir=int(r["nas"]), tod=int(r["tod"]),
                 fecha=r["fecha"])
        filas.append(f)

        # 3 controles: mismo minuto de reloj, otros dias al azar
        n = 0
        intentos = 0
        while n < 3 and intentos < 40:
            intentos += 1
            fc = fechas[int(rng.integers(0, len(fechas)))]
            if fc == r["fecha"]:
                continue
            g = rasgos(idx, fc, int(r["tod"]))
            if g is None:
                continue
            g.update(tipo="CONTROL", dir=int(r["nas"]), tod=int(r["tod"]),
                     fecha=fc)
            filas.append(g)
            n += 1

    D = pd.DataFrame(filas)
    ent = D[D["tipo"] == "ENTRADA"]
    con = D[D["tipo"] == "CONTROL"]
    print("Emparejado: %d entradas contra %d controles" % (len(ent), len(con)))
    print()

    campos = ["r5", "r15", "r30", "r60", "r120", "pos_rango",
              "rango_bp", "vol30", "dist_hi", "dist_lo"]

    for d, nom in [(1, "LARGOS"), (-1, "CORTOS")]:
        A = ent[ent["dir"] == d]
        B = con[con["dir"] == d]
        print("=" * 92)
        print("  %s   (%d entradas vs %d controles)" % (nom, len(A), len(B)))
        print("=" * 92)
        print("  %-11s %11s %11s %11s %8s %9s"
              % ("rasgo", "entradas", "controles", "diferencia", "t", "p"))
        print("  " + "-" * 88)
        for c in campos:
            a = A[c].dropna().to_numpy()
            b = B[c].dropna().to_numpy()
            if len(a) < 30 or len(b) < 30:
                continue
            t, p = stats.ttest_ind(a, b, equal_var=False)
            flag = ""
            if p < 0.001:
                flag = "  ***"
            elif p < 0.01:
                flag = "  **"
            elif p < 0.05:
                flag = "  *"
            print("  %-11s %+11.2f %+11.2f %+11.2f %8.2f %9.5f%s"
                  % (c, a.mean(), b.mean(), a.mean() - b.mean(), t, p, flag))
        print()

    print("Umbral con 10 rasgos x 2 direcciones = 20 pruebas:")
    print("  p < 0.0025 para significancia al 5% (Bonferroni)")
    D.to_csv("forense_rasgos.csv", index=False)
    print()
    print("Guardado forense_rasgos.csv (%d filas)" % len(D))


if __name__ == "__main__":
    main()
