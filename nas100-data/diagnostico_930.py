#!/usr/bin/env python3
"""
Que pasa exactamente en las 09:30 de los datos de Dukascopy.

Si usatechidxusd cotiza ~22h/dia no es el indice oficial (que solo se
publica 09:30-16:00), sino un CFD continuo. En ese caso el "retraso de
apertura" que propuse como explicacion no puede ser la causa, y hay
que buscar la discontinuidad real.

Mide:
  1. Cobertura horaria: cuantas velas por hora hay de verdad.
  2. Salto en 09:30: open[09:30] contra close[09:29].
  3. De donde sale el empuje: descompone el movimiento 09:30->09:45
     en el primer minuto y el resto.
"""
import glob
import os
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
OPEN_MIN = 9 * 60 + 30


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    et = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    return df.assign(fecha=et.dt.date,
                     tod=et.dt.hour * 60 + et.dt.minute,
                     dow=et.dt.dayofweek)


def main():
    df = cargar()
    lab = df[df["dow"] < 5]
    print("Velas totales (dias laborables): %d" % len(lab))

    #--- 1. cobertura horaria ----------------------------------------
    print("\n1. VELAS POR HORA (hora de Nueva York)")
    porh = lab.groupby(lab["tod"] // 60).size()
    ndias = lab["fecha"].nunique()
    print("   dias: %d" % ndias)
    linea = ""
    for h in range(24):
        v = int(porh.get(h, 0))
        linea += "%02d:%5.0f  " % (h, v / ndias)
        if h % 6 == 5:
            print("   " + linea)
            linea = ""
    print("   (velas por dia y hora; 60 = hora completa)")

    #--- 2. salto en 09:30 -------------------------------------------
    print("\n2. DISCONTINUIDAD EN 09:30")
    filas = []
    for fecha, g in lab.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        i29 = np.where(tod == OPEN_MIN - 1)[0]
        i30 = np.where(tod == OPEN_MIN)[0]
        i45 = np.where(tod == OPEN_MIN + 15)[0]
        i31 = np.where(tod == OPEN_MIN + 1)[0]
        if not (len(i29) and len(i30) and len(i45) and len(i31)):
            continue
        c29 = float(c[i29[0]])
        o30 = float(o[i30[0]])
        o31 = float(o[i31[0]])
        o45 = float(o[i45[0]])
        filas.append(dict(
            salto_2930=(o30 / c29 - 1) * 1e4,
            min1=(o31 / o30 - 1) * 1e4,
            resto=(o45 / o31 - 1) * 1e4,
            total=(o45 / o30 - 1) * 1e4))
    d = pd.DataFrame(filas)
    print("   sesiones con las 4 velas: %d" % len(d))
    print("   %-28s %8s %8s %8s" % ("", "media", "sd", "|media|"))
    for col, nom in [("salto_2930", "open[9:30] vs close[9:29]"),
                     ("min1", "primer minuto 9:30->9:31"),
                     ("resto", "resto 9:31->9:45"),
                     ("total", "total 9:30->9:45")]:
        print("   %-28s %+8.2f %8.2f %8.2f"
              % (nom, d[col].mean(), d[col].std(), d[col].abs().mean()))

    #--- 3. de donde sale el empuje ----------------------------------
    print("\n3. CUANTO DEL EMPUJE 9:30->9:45 ESTA EN EL PRIMER MINUTO")
    print("   |min1| medio / |total| medio = %.1f%%"
          % (100.0 * d["min1"].abs().mean() / d["total"].abs().mean()))
    print("   correlacion min1 vs resto: %+.4f" % d["min1"].corr(d["resto"]))
    print("   -> si es muy negativa, el primer minuto se REVIERTE")
    print("      y medir desde el es capturar algo que se deshace.")

    #--- 4. es el primer minuto anormalmente grande? -----------------
    print("\n4. TAMANO DEL PRIMER MINUTO FRENTE A LOS SIGUIENTES")
    tam = []
    for fecha, g in lab.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        for k in range(0, 6):
            i = np.where(tod == OPEN_MIN + k)[0]
            if len(i):
                tam.append((k, abs((c[i[0]] / o[i[0]] - 1) * 1e4)))
    t = pd.DataFrame(tam, columns=["min", "rango_bp"])
    print("   minuto tras apertura -> |movimiento| medio en bp")
    for k, v in t.groupby("min")["rango_bp"].mean().items():
        print("     +%d min:  %6.2f bp" % (k, v))


if __name__ == "__main__":
    main()
