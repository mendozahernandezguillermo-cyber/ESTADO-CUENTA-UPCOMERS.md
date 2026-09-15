#!/usr/bin/env python3
"""
Los dos feeds dan precios distintos a la misma hora. Dos causas posibles:

  A) DESFASE HORARIO. El 15:45 del broker no es el 15:45 que yo asumo.
     Seria un error de calibracion y tendria arreglo.
  B) SERIES DISTINTAS. NACUSD.c deriva del E-mini y usatechidxusd sigue
     al cash. La base entre futuro y cash se mueve. No tendria arreglo:
     mi backtest de 15 anos no describiria el instrumento operable.

Test: para cada precio observado en el Journal del Probador, busco en MIS
datos el minuto de ese dia cuyo precio mas se le parece. Si todos apuntan
al mismo desplazamiento, es (A). Si apuntan a cualquier lado, es (B).
"""
import glob
import os
import numpy as np
import pandas as pd
import datetime as dt

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

# (fecha, minuto_servidor, bid observado en el Journal)
OBS = [
    ("2026-03-02", 945, 24791.97), ("2026-03-02", 1300, 24963.52),
    ("2026-03-05", 945, 25012.55), ("2026-03-05", 1300, 24946.85),
    ("2026-03-09", 945, 24508.15), ("2026-03-09", 1300, 24928.85),
    ("2026-03-10", 945, 25077.65), ("2026-03-10", 1300, 24988.65),
    ("2026-03-12", 945, 24615.45), ("2026-03-12", 1300, 24541.05),
    ("2026-03-17", 945, 24854.35), ("2026-03-17", 1300, 24791.95),
    ("2026-03-19", 945, 24246.75), ("2026-03-19", 1300, 24401.65),
    ("2026-03-20", 945, 24063.55), ("2026-03-20", 1300, 23957.65),
    ("2026-03-24", 945, 24030.55), ("2026-03-24", 1300, 24293.65),
]

# servidor = Chicago + 7 ; Nueva York = Chicago + 1 ; luego NY = servidor - 6
DESPL_NY = -6 * 60


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*2026*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    et = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    return df.assign(fecha=et.dt.date,
                     tod=et.dt.hour * 60 + et.dt.minute)


def main():
    df = cargar()
    print("Para cada precio del Journal: en que minuto de MIS datos aparece")
    print("ese precio, y cuanto se desvia del minuto esperado.")
    print()
    print("fecha        min_srv  esperado_NY  precio_obs  mi_precio   dif_pts"
          "  mejor_NY  desfase_min")
    print("-" * 96)

    desfases = []
    difs = []
    for f, msrv, px in OBS:
        fecha = dt.date.fromisoformat(f)
        g = df[df["fecha"] == fecha]
        if len(g) == 0:
            print("%s  sin datos" % f)
            continue
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)

        esperado = msrv + DESPL_NY
        i = np.argmin(np.abs(tod - esperado))
        mio = o[i]
        dif = px - mio

        j = int(np.argmin(np.abs(o - px)))       # minuto que mejor encaja
        desf = int(tod[j] - esperado)
        desfases.append(desf)
        difs.append(dif)

        print("%s  %7d  %11d  %10.2f  %9.2f  %+8.1f  %8d  %+11d"
              % (f, msrv, esperado, px, mio, dif, tod[j], desf))

    d = np.array(desfases)
    v = np.array(difs)
    print("-" * 96)
    print("Diferencia de precio: media %+.1f pts, |media| %.1f pts, sd %.1f"
          % (v.mean(), np.abs(v).mean(), v.std()))
    print("Desfase implicito: mediana %+.0f min, sd %.0f min, rango %d..%d"
          % (np.median(d), d.std(), d.min(), d.max()))
    print()
    if d.std() < 20:
        print("VEREDICTO: desfase consistente -> es un error de calibracion (A).")
    else:
        print("VEREDICTO: el desfase apunta a cualquier lado -> los precios no")
        print("           se explican por un desplazamiento horario. Son SERIES")
        print("           DISTINTAS (B). Mi backtest no describe NACUSD.c.")

    #--- contraste directo: cuanto se separan los dos feeds al cierre ----
    print()
    print("Contraste independiente: precio al cierre de sesion de cada dia")
    print("frente al mismo dia en mis datos (base futuro vs cash).")
    for f, msrv, px in OBS:
        if msrv != 1300:
            continue
        fecha = dt.date.fromisoformat(f)
        g = df[df["fecha"] == fecha]
        if len(g) == 0:
            continue
        tod = g["tod"].to_numpy(); o = g["open"].to_numpy(float)
        i = np.argmin(np.abs(tod - (1300 + DESPL_NY)))
        print("  %s  broker %9.2f   yo %9.2f   base %+8.1f pts (%+.1f bp)"
              % (f, px, o[i], px - o[i], (px / o[i] - 1) * 1e4))


if __name__ == "__main__":
    main()
