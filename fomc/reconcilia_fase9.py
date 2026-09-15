#!/usr/bin/env python3
"""
RECONCILIACION: -99,0 bp contra los -133,4 bp de la Fase 9

El desacuerdo. `con_tp_y_stop.py` da como peor relleno realizado -99,0 bp
(1,36% de la cuenta). La Fase 9 y `mql5/riesgo_de_salto.py` dan -133,4 bp
(1,84%), con deslizamiento maximo 54,1 bp sobre 9 stops ejecutados. Las dos
mediciones dicen usar los mismos M1 y los mismos 117 eventos.

La hipotesis. `riesgo_de_salto.py` linea 40 fija `TP_BP = 80.0`: es la
configuracion SIMETRICA +-80, anterior a bajar el take profit a 40. Con el TP
en 80 la posicion se queda abierta mucho mas tiempo —llegar a +80 es mas dificil
que llegar a +40— y por tanto sigue viva cuando llegan los huecos nocturnos. Con
el TP en 40 sale antes y se libra.

Si es eso, cambiando SOLO el TP mi simulador tiene que reproducir las cifras de
la Fase 9. Y si las reproduce, ninguna de las dos mediciones esta mal: contestan
preguntas distintas y las dos son correctas para su configuracion.

Prediccion registrada ANTES de correrlo:
  - con TP=80 salen 9 stops, deslizamiento maximo ~54 bp y peor evento ~-133 bp
  - el evento 2022-01-26 es el que cambia: con TP=80 se para en el stop tras un
    hueco; con TP=40 sale por take profit ANTES del hueco
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import con_tp_y_stop as C
from ventana_nocturna import CSV_FECHAS, EXCLUIR, carga, mapas_por_dia, noches

CLAVE = pd.Timestamp("2022-01-26").date()


def corre(ohlc, ev, tp_bp):
    """Simula todos los eventos con un TP dado. Devuelve (dict fecha->res)."""
    orig = C.TP_BP
    C.TP_BP = tp_bp
    try:
        out = {}
        for s, e in ev:
            z = C.simula(ohlc, s, e)
            if z:
                out[s] = z
        return out
    finally:
        C.TP_BP = orig


def resume(res, tp_bp):
    r = np.array([v[0] for v in res.values()])
    mot = [v[1] for v in res.values()]
    stops = [v for v in res.values() if v[1].startswith("stop")]
    desliz = [abs(v[0]) - C.STOP_BP for v in stops if abs(v[0]) > C.STOP_BP]
    print("  TP = %g bp" % tp_bp)
    print("     eventos                        : %d" % len(r))
    print("     salidas: 09:30 %d · take profit %d · stop %d"
          % (sum(1 for m in mot if m == "cierre_0930"),
             sum(1 for m in mot if m.startswith("tp")),
             len(stops)))
    print("     stops ejecutados               : %d" % len(stops))
    print("     de ellos PEOR que -%g bp       : %d" % (C.STOP_BP, len(desliz)))
    if desliz:
        print("     deslizamiento maximo           : %.1f bp" % max(desliz))
        print("     deslizamiento medio cuando pasa: %.1f bp"
              % (sum(desliz) / len(desliz)))
    print("     PEOR EVENTO                    : %+.1f bp" % r.min())
    print("     media                          : %+.2f bp" % r.mean())
    return r


def main():
    f = pd.read_csv(CSV_FECHAS, parse_dates=["fecha"])
    f = f[~f["fecha"].dt.strftime("%Y-%m-%d").isin(EXCLUIR)]
    fechas = set(f["fecha"].dt.date)

    print("cargando ...")
    mapas = mapas_por_dia(carga())
    ev = [(s, e) for s, e in noches(mapas) if s in fechas]
    dias = set()
    for s, e in ev:
        dias.add(s)
        dias.add(e)
    ohlc = C.carga_ohlc(dias)
    print("eventos: %d" % len(ev))

    print()
    print("=" * 78)
    print("EL MISMO SIMULADOR, CAMBIANDO SOLO EL TAKE PROFIT")
    print("=" * 78)
    r40 = corre(ohlc, ev, 40.0)
    r80 = corre(ohlc, ev, 80.0)
    print()
    resume(r40, 40.0)
    print()
    resume(r80, 80.0)

    print()
    print("=" * 78)
    print("CONTRA LO QUE PUBLICA LA FASE 9 (riesgo_de_salto.py, TP=80)")
    print("=" * 78)
    ref = [("salidas por stop", 9), ("stops peor que -80 bp", 5),
           ("deslizamiento maximo (bp)", 54.1), ("peor evento (bp)", -133.4),
           ("deslizamiento medio (bp)", 19.7)]
    stops80 = [v for v in r80.values() if v[1].startswith("stop")]

    # OJO A LA DEFINICION, que es el residuo del desacuerdo.
    # riesgo_de_salto.py mide el deslizamiento contra el precio del STOP:
    #     desliz = (sl / o - 1) x 1e4
    # y yo lo media contra el de ENTRADA:
    #     desliz = |ret| - STOP_BP
    # Las dos son correctas y difieren en el termino de composicion: 54,1
    # contra 53,4 bp en el peor caso. Aqui se usa la suya para que la
    # comparacion sea homologable.
    def desliz_fase9(ret_bp):
        """De un retorno de relleno a deslizamiento medido sobre el stop."""
        o_sobre_e = 1.0 + ret_bp / 1e4              # open del hueco / entrada
        sl_sobre_e = 1.0 - C.STOP_BP / 1e4          # nivel del stop / entrada
        return (sl_sobre_e / o_sobre_e - 1.0) * 1e4

    d80 = [desliz_fase9(v[0]) for v in stops80
           if desliz_fase9(v[0]) > 0.001]
    mio = {"salidas por stop": len(stops80),
           "stops peor que -80 bp": len(d80),
           "deslizamiento maximo (bp)": max(d80) if d80 else 0.0,
           "peor evento (bp)": min(v[0] for v in r80.values()),
           "deslizamiento medio (bp)": (sum(d80) / len(d80)) if d80 else 0.0}
    print("  %-30s%12s%12s%10s" % ("magnitud", "Fase 9", "este script", "¿cuadra?"))
    print("  " + "-" * 66)
    ok = True
    for nom, val in ref:
        v = mio[nom]
        cuadra = abs(v - val) <= max(0.2, abs(val) * 0.01)
        ok = ok and cuadra
        print("  %-30s%12.1f%12.1f%10s"
              % (nom, val, v, "si" if cuadra else "NO"))
    print()
    print("  -> %s" % ("las dos mediciones coinciden: el desacuerdo era el TP"
                       if ok else "siguen sin cuadrar, hay otra causa"))

    print()
    print("=" * 78)
    print("EL EVENTO QUE CAMBIA  ·  %s" % CLAVE)
    print("=" * 78)
    if CLAVE in r40 and CLAVE in r80:
        print("  con TP=40 : %+8.1f bp   salida por %s" % (r40[CLAVE][0], r40[CLAVE][1]))
        print("  con TP=80 : %+8.1f bp   salida por %s" % (r80[CLAVE][0], r80[CLAVE][1]))
        print()
        print("  Es el mismo evento y la misma senda de precios. Con el TP a 40")
        print("  la posicion ya estaba cerrada cuando llego el hueco; con el TP")
        print("  a 80 seguia abierta y el stop rellenó %.1f bp por debajo del"
              % desliz_fase9(r80[CLAVE][0]))
        print("  nivel. El TP corto no solo trunca la cola buena: quita la mala.")
    else:
        print("  el evento no esta en la muestra con datos")

    # cuanto vale eso en la unidad que decide
    print()
    print("=" * 78)
    print("LO QUE ESTO CAMBIA EN LA DECISION")
    print("=" * 78)
    CUENTA, RIESGO = 25000.0, 0.0110
    apal = RIESGO / (C.STOP_BP / 1e4)
    marg = {}
    for tp, r in (("40", r40), ("80", r80)):
        peor = min(v[0] for v in r.values())
        pct = abs(peor) / 1e4 * apal * 100.0
        marg[tp] = 100.0 * (1 - pct / 2.0)
        print("  TP=%s : peor evento %+7.1f bp = %.2f%% de la cuenta  ->  %s"
              % (tp, peor, pct,
                 "ROMPE el 2%" if pct > 2.0 else "dentro, margen %.0f%%"
                 % marg[tp]))
    print()
    print("  Con el riesgo al 1,10% las dos configuraciones aguantan el limite")
    print("  por operacion, asi que la discrepancia no cambiaba ninguna")
    print("  decision. Pero el margen contra el hard breach es %.0f%% con TP=40"
          % marg["40"])
    print("  y %.0f%% con TP=80: elegir el TP era tambien decidir sobre el 2%%"
          % marg["80"])
    print("  por operacion, y en la Fase 12 no estaba contado como tal.")


if __name__ == "__main__":
    main()
