#!/usr/bin/env python3
"""
TEST DE ALEATORIZACION DE LA NOCHE PRE-FOMC

Por que hace falta. `ventana_nocturna.py` mide +26,2 bp en las 117 noches
pre-FOMC y el contraste contra controles emparejados da t entre 1,83 y 3,05
segun el control que se elija. Peor: el placebo a -14 dias —noches SIN anuncio—
da +19,2 bp con t=2,41, mas significativo que el efecto real contra uno de los
controles. Con cuatro placebos no se puede decidir nada: cuatro intentos dan un
p<0,05 por azar el 18% de las veces.

Lo que hace este script. Construye la distribucion nula por aleatorizacion, que
no supone normalidad y contesta la pregunta exacta que importa:

    ¿es +26,2 bp un valor raro entre conjuntos de 117 noches de miercoles?

Dos disenos, porque miden cosas distintas:

  1. ALEATORIZACION. 20.000 muestras de 117 noches de miercoles sin anuncio.
     Da el p-valor empirico del efecto contra la poblacion de miercoles.
  2. BARRIDO DE DESPLAZAMIENTOS. Los mismos 117 eventos movidos k semanas.
     Es un placebo estructurado: conserva la posicion en el calendario y el
     dia de la semana, y solo quita el anuncio. Si el desplazamiento 0 no
     destaca sobre los demas, el efecto es del calendario y no del FOMC.

El 2 es mas exigente que el 1 y es el que decide.

Prediccion registrada ANTES de correrlo:
  - si el efecto es del FOMC, el desplazamiento 0 es el maximo del barrido
  - si es del calendario, el 0 queda en medio de los demas
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ventana_nocturna import (CSV_FECHAS, EXCLUIR, ENTRADA, SALIDA,
                              carga, mapas_por_dia, noches, retorno)

SEMILLA = 20260915
N_MUESTRAS = 20000
DESPLAZAMIENTOS = list(range(-42, 43, 7))     # -6 a +6 semanas, en semanas


def main():
    f = pd.read_csv(CSV_FECHAS, parse_dates=["fecha"])
    f = f[~f["fecha"].dt.strftime("%Y-%m-%d").isin(EXCLUIR)]
    fechas = set(f["fecha"].dt.date)

    print("cargando M1 ...")
    px = carga()
    mapas = mapas_por_dia(px)
    todas = noches(mapas)
    print("dias utilizables: %d · noches: %d" % (len(mapas), len(todas)))

    ret = {}
    for s, e in todas:
        v = retorno(mapas, s, e, ENTRADA, SALIDA)
        if v is not None:
            ret[s] = v

    ev_dias = [s for s, _ in todas if s in fechas and s in ret]
    x = np.array([ret[d] for d in ev_dias])
    print("noches pre-FOMC medidas: %d · media %+.2f bp" % (len(x), x.mean()))

    # ---------------------------------------------------- 1. aleatorizacion
    # Poblacion: noches de miercoles sin anuncio. Se restringe al dia de la
    # semana porque el 95% de los anuncios cae en miercoles y la noche del
    # martes no es una noche cualquiera.
    pool = np.array([v for d, v in ret.items()
                     if d.weekday() == 2 and d not in fechas])
    rng = np.random.default_rng(SEMILLA)
    n = len(x)
    medias = np.array([rng.choice(pool, size=n, replace=False).mean()
                       for _ in range(N_MUESTRAS)])
    p_emp = float((medias >= x.mean()).mean())

    print()
    print("=" * 78)
    print("1. ALEATORIZACION  ·  %d muestras de %d noches de miercoles"
          % (N_MUESTRAS, n))
    print("=" * 78)
    print("  poblacion (miercoles sin anuncio) : n=%d · media %+.2f bp"
          % (len(pool), pool.mean()))
    print("  efecto observado                  : %+.2f bp" % x.mean())
    print("  percentiles de la nula            : p50 %+.2f · p95 %+.2f · p99 %+.2f"
          % (np.percentile(medias, 50), np.percentile(medias, 95),
             np.percentile(medias, 99)))
    print("  p-valor empirico (una cola)       : %.4f" % p_emp)

    # ---------------------------------------------------- 2. barrido
    print()
    print("=" * 78)
    print("2. BARRIDO DE DESPLAZAMIENTOS  ·  los mismos eventos, movidos")
    print("=" * 78)
    print("  %10s%8s%11s%9s   %s" % ("desplaz.", "n", "media bp", "z", ""))
    print("  " + "-" * 62)
    sd_pool = pool.std(ddof=1)
    filas = []
    for k in DESPLAZAMIENTOS:
        dias = [d - pd.Timedelta(days=k) for d in ev_dias]
        vals = [ret[d] for d in dias if d in ret]
        if len(vals) < 60:
            continue
        v = np.array(vals)
        z = (v.mean() - pool.mean()) / (sd_pool / np.sqrt(len(v)))
        filas.append((k, len(v), v.mean(), z))
        marca = "  <== los eventos de verdad" if k == 0 else ""
        print("  %10s%8d%11.2f%9.2f   %s"
              % ("%+d d" % k if k else "0 (real)", len(v), v.mean(), z, marca))

    reales = [r for r in filas if r[0] == 0][0]
    otros = [r for r in filas if r[0] != 0]
    peores = sorted(otros, key=lambda r: -r[2])
    print()
    print("  El desplazamiento real da %+.2f bp." % reales[2])
    print("  De los %d placebos, %d dan una media IGUAL O MAYOR."
          % (len(otros), sum(1 for r in otros if r[2] >= reales[2])))
    print("  Los tres placebos mas altos: %s"
          % ", ".join("%+dd %+.1f bp" % (r[0], r[2]) for r in peores[:3]))
    rango = max(r[2] for r in otros) - min(r[2] for r in otros)
    print("  Rango de los placebos: %.1f bp — el efecto que se busca es de"
          " 13 a 20 bp." % rango)

    # ------------------------------------------- 3. por tramos, con su propia nula
    # La prima overnight cambia de nivel entre epocas, asi que la poblacion de
    # referencia tiene que ser del MISMO tramo. Comparar 2021-2026 contra la
    # nula de 15 anos mezclaria dos cosas.
    print()
    print("=" * 78)
    print("3. POR TRAMOS  ·  cada uno contra la nula de SU epoca")
    print("=" * 78)
    print("  %-12s%5s%10s%10s%9s%9s%9s"
          % ("tramo", "n", "FOMC", "nula", "exceso", "p emp.", "2se"))
    print("  " + "-" * 66)
    tramos = [("2011-2015", 2011, 2015), ("2016-2020", 2016, 2020),
              ("2021-2026", 2021, 2026), ("2016-2026", 2016, 2026),
              ("TODO", 2011, 2026)]
    res = {}
    for etq, a, b in tramos:
        xt = np.array([ret[d] for d in ev_dias if a <= d.year <= b])
        pt = np.array([v for d, v in ret.items()
                       if d.weekday() == 2 and d not in fechas
                       and a <= d.year <= b])
        if len(xt) < 10 or len(pt) < 40:
            continue
        m = np.array([rng.choice(pt, size=len(xt), replace=False).mean()
                      for _ in range(N_MUESTRAS)])
        p = float((m >= xt.mean()).mean())
        se = m.std(ddof=1)
        res[etq] = (xt.mean(), pt.mean(), xt.mean() - pt.mean(), p, se)
        print("  %-12s%5d%10.2f%10.2f%9.2f%9.4f%9.2f"
              % (etq, len(xt), xt.mean(), pt.mean(),
                 xt.mean() - pt.mean(), p, 2 * se))

    # ------------------------------------------- 4. neto de friccion
    CUENTA, RIESGO, STOP_BP = 25000.0, 0.0110, 80.0
    SPREAD_BP, SWAP_ANUAL, UNID_ANIO = 1.37, 0.064, 364.0
    bp_unidad = SWAP_ANUAL / UNID_ANIO * 1e4
    ida_vuelta = 2 * SPREAD_BP

    print()
    print("=" * 78)
    print("4. NETO DE FRICCION  ·  regla de dimensionado de la Fase 12.1")
    print("=" * 78)
    print("  ida y vuelta %.2f bp · una unidad de swap %.2f bp del nocional"
          % (ida_vuelta, bp_unidad))
    print()
    print("  %-12s%9s%8s%9s%9s%12s"
          % ("tramo", "exceso", "unid.", "friccion", "neto", "f defendible"))
    print("  " + "-" * 62)
    for etq in ("TODO", "2016-2026", "2021-2026"):
        if etq not in res:
            continue
        exceso, _, _, _, se = res[etq][0], 0, res[etq][2], 0, res[etq][4]
        exceso = res[etq][2]
        for unid in (1, 3):
            fr = ida_vuelta + unid * bp_unidad
            neto = exceso - fr
            defend = neto - 2 * se
            print("  %-12s%9.2f%8d%9.2f%9.2f%12s"
                  % (etq, exceso, unid, fr, neto,
                     "f = 0" if defend <= 0 else "%+.2f bp" % defend))
    print()
    print("  El signo de la ultima columna lo decide UN dato no verificado:")
    print("  si el rollover del martes al miercoles cobra 1 unidad o 3.")
    print("  mql5/Medir_Swap_Unidades.mq5 lo resuelve en una semana.")

    print()
    print("=" * 78)
    print("LECTURA")
    print("=" * 78)
    if p_emp < 0.05 and sum(1 for r in otros if r[2] >= reales[2]) == 0:
        print("  El efecto sobrevive a los dos disenos: es raro contra la")
        print("  poblacion de miercoles Y es el maximo del barrido.")
    elif p_emp < 0.05:
        print("  Pasa la aleatorizacion pero NO domina el barrido: hay noches")
        print("  sin anuncio que rinden lo mismo. Eso apunta a calendario, no")
        print("  a FOMC, y el diseño no puede separar las dos cosas con n=%d." % n)
    else:
        print("  No pasa ninguno de los dos. La ventaja no es distinguible")
        print("  del ruido de las noches de miercoles.")


if __name__ == "__main__":
    main()
