#!/usr/bin/env python3
"""
CONTROL POSITIVO del detector.

Un detector que nunca ha disparado no esta validado.

Version 2. La v1 tenia un bug: c2 no evolucionaba dentro del episodio, asi
que R5 (asimetria) y R6 (duracion) median sobre ceros y no podian disparar.
Aqui c2 se reparte a lo largo del episodio, de modo que
Delta c2 = resultado realizado, igual que en el journal real. Y las
perdedoras se alargan ENTRE registros, no despues del ultimo.

  A) MARTINGALA: 80% de episodios ganan poco y rapido; 20% van en contra,
     doblan el tamano en cada paso, anaden posiciones, duran mucho y
     pierden mucho.
  B) GRID: 65% ganan poco; 35% van en contra, abren en rejilla y cubren
     con largo y corto simultaneos.
"""
import numpy as np
import pandas as pd
from detector_grid import analizar

RNG = np.random.default_rng(1234)
T0 = 1_658_860_467_000


def fabricar(modo, n_ep=800):
    filas = []
    t = T0
    c2 = 0.0

    for _ in range(n_ep):
        t += int(RNG.uniform(2, 20) * 3_600_000)
        adverso = RNG.random() < (0.20 if modo == "martingala" else 0.35)
        pasos = int(RNG.integers(4, 11) if adverso else RNG.integers(1, 4))
        tam = 5.0
        c3 = 0.0
        n_ab = 1
        ini = len(filas)

        for k in range(pasos):
            if adverso:
                c3 -= abs(RNG.normal(1.1, 0.5))
                if modo == "martingala":
                    tam *= 2.0                      # DOBLA en perdida
                    n_ab = min(7, n_ab + (1 if k % 2 else 0))
                else:
                    tam *= 1.35
                    n_ab = min(7, n_ab + 1)         # rejilla: abre mas
                # las perdedoras se alargan ENTRE registros
                paso_min = RNG.uniform(300, 1200)
            else:
                c3 += abs(RNG.normal(0.22, 0.09))
                paso_min = RNG.uniform(15, 90)

            inst = "+NASDAQ 100 (Mini)"
            if modo == "grid" and adverso and k >= 2 and RNG.random() < 0.55:
                inst = "±NASDAQ 100 (Mini)"         # cobertura

            t += int(paso_min * 60_000)
            filas.append([0.0, t, np.nan, c3, abs(c3) * 5, tam,
                          0.0, k, n_ab, inst, 0.0])

        # resultado realizado del episodio
        real = c3 * (1.7 if adverso else 1.0)
        # c2 se reparte linealmente por las filas del episodio, de forma que
        # c2[ultima] - c2[primera] = real   (igual que en el journal real)
        m = len(filas) - ini
        for j in range(m):
            filas[ini + j][2] = c2 + real * (j / max(1, m - 1)) if m > 1 \
                else c2
        c2 += real

        t += 60_000
        filas.append([0.0, t, c2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0])

    df = pd.DataFrame(filas, columns=["c%d" % i for i in range(11)])
    df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
    df["c9s"] = df["c9"].astype(str)
    df["plano"] = df["c9s"] == ""
    df["ep"] = (df["plano"] != df["plano"].shift()).cumsum()
    return df


res = {}
for modo, etq in [("martingala", "CONTROL POSITIVO A — MARTINGALA sintetica"),
                  ("grid", "CONTROL POSITIVO B — GRID sintetica")]:
    r = analizar(fabricar(modo), etq)
    res[modo] = r
    print()

print("=" * 74)
print("VALIDACION DEL DETECTOR")
print("=" * 74)
print("Para que el veredicto 'LIMPIO' sobre THL signifique algo, los dos")
print("controles positivos tienen que salir RECHAZADOS (>=4 banderas).")
print()
ok = True
for modo, r in res.items():
    est = "PASA" if r["n"] >= 4 else "FALLA"
    if r["n"] < 4:
        ok = False
    print("  %-12s  banderas %d/6  ->  %s" % (modo, r["n"], est))
print()
print("DETECTOR %s" % ("VALIDADO" if ok else
                       "NO VALIDADO — no fiarse del veredicto sobre THL"))
