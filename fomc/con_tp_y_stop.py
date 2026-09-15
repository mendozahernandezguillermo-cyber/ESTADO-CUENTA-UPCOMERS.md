#!/usr/bin/env python3
"""
LA VENTANA CON EL TP Y EL STOP PUESTOS  —  lo que opera el EA de verdad

`ventana_nocturna.py` mide el retorno de la ventana en bruto: entra a las 15:57
NY del dia anterior y sale a las 09:30 NY del dia del anuncio, sin nada en medio.
Eso NO es lo que opera EA_FOMC_Gap. Segun su codigo (lineas 552-566) el EA:

    - abre LARGO a mercado (ORDER_TYPE_BUY), nunca corto
    - pone sl = ask x (1 - 80 bp)  y  tp = ask x (1 + 40 bp) EN EL SERVIDOR
    - y si ninguno se toca, cierra a las 09:30 NY

Con el TP a 40 bp y el stop a 80 la distribucion queda truncada por arriba a la
mitad de distancia que por abajo. Eso cambia la media, y la Fase 12 ya lo midio
barriendo el TP: 19,4 bp sin TP contra 15,4 bp con TP de 50. La pregunta de este
script es si ese descuento se come la unica esquina en la que la Fase 12.1
concedia tamano (+2,59 bp).

COMO SE SIMULA, y donde estan las decisiones que importan:

  1. Se camina la senda M1 barra a barra. Truncar el retorno de cierre no vale:
     el TP se toca DENTRO del dia y esa fue la equivocacion que la propia Fase 12
     dejo anotada.
  2. Si el OPEN de una barra ya esta pasado el nivel, se rellena al OPEN, no al
     nivel. Eso es el hueco, y es la unica forma de que aparezca el
     deslizamiento que la Fase 9 midio (5 de 9 stops rellenaron peor que -80 bp,
     deslizamiento maximo 54,1 bp, peor evento real -133,4 bp).
  3. Si en la MISMA barra el low toca el stop y el high toca el TP, el orden es
     indeterminable con M1. Se reportan las dos convenciones y el recuento de
     barras ambiguas, en vez de elegir una y callarse.
  4. El control recibe EXACTAMENTE el mismo tratamiento: largo, mismo TP, mismo
     stop, misma hora. Comparar una ventana con TP contra otra sin TP mediria
     el TP, no el FOMC.

Prediccion registrada ANTES de correrlo:
  - la media baja respecto a los +26,19 bp en bruto (el TP trunca la cola buena)
  - el exceso sobre el control baja MENOS que la media, porque el control tambien
    pierde su cola por el mismo TP
  - el peor evento es peor que -80 bp, por huecos
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ventana_nocturna import (CSV_FECHAS, DIR_M1, EXCLUIR, ENTRADA, SALIDA,
                              carga, mapas_por_dia, noches)

STOP_BP = 80.0
TP_BP = 40.0
SPREAD_BP, SWAP_ANUAL, UNID_ANIO = 1.37, 0.064, 364.0
SEMILLA = 20260915
N_MUESTRAS = 20000

HM_NOCHE_INI = 15 * 60 + 50      # margen antes de la entrada
HM_NOCHE_FIN = 10 * 60           # margen despues de la salida


def carga_ohlc(dias):
    """OHLC de la franja nocturna, solo de los dias pedidos.

    dia -> (hm[], open[], high[], low[], close[]) ordenado por hm.
    """
    trozos = []
    for p in sorted(glob.glob(os.path.join(DIR_M1, "usatechidxusd-m1-*.csv"))):
        d = pd.read_csv(p, usecols=["timestamp", "open", "high", "low", "close"])
        ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
        ny = ts.dt.tz_convert("America/New_York")
        hm = ny.dt.hour * 60 + ny.dt.minute
        dia = ny.dt.date
        m = ((hm >= HM_NOCHE_INI) | (hm <= HM_NOCHE_FIN)) & dia.isin(dias)
        if not m.any():
            continue
        trozos.append(pd.DataFrame({
            "dia": dia[m].values, "hm": hm[m].values,
            "o": d["open"][m].values, "h": d["high"][m].values,
            "l": d["low"][m].values, "c": d["close"][m].values}))
    if not trozos:
        raise SystemExit("sin barras nocturnas")
    px = pd.concat(trozos, ignore_index=True).sort_values(["dia", "hm"])
    out = {}
    for dia, g in px.groupby("dia", sort=True):
        out[dia] = (g["hm"].values, g["o"].values, g["h"].values,
                    g["l"].values, g["c"].values)
    return out


def senda(ohlc, d_ent, d_sal):
    """Barras de la noche, en orden: entrada+1 .. fin de dia, 00:00 .. salida."""
    tramos = []
    if d_ent in ohlc:
        hm, o, h, l, c = ohlc[d_ent]
        m = hm > ENTRADA
        tramos.append((hm[m], o[m], h[m], l[m], c[m]))
    if d_sal in ohlc:
        hm, o, h, l, c = ohlc[d_sal]
        m = hm <= SALIDA
        tramos.append((hm[m], o[m], h[m], l[m], c[m]))
    if not tramos:
        return None
    return [np.concatenate([t[i] for t in tramos]) for i in range(5)]


def precio_entrada(ohlc, d_ent):
    """Ultimo cierre en o antes de 15:57 del dia de entrada."""
    if d_ent not in ohlc:
        return None
    hm, _, _, _, c = ohlc[d_ent]
    m = (hm <= ENTRADA) & (hm >= ENTRADA - 45)
    if not m.any():
        return None
    return float(c[m][-1])


def simula(ohlc, d_sal, d_ent, orden_ambiguo="stop"):
    """Un evento. Devuelve (ret_bp, motivo, ambigua) o None.

    orden_ambiguo: si en una barra caben stop y TP, cual se supone primero.
    """
    e = precio_entrada(ohlc, d_ent)
    if e is None or e <= 0:
        return None
    s = senda(ohlc, d_ent, d_sal)
    if s is None or len(s[0]) < 30:
        return None
    hm, o, h, l, c = s

    n_sl = e * (1.0 - STOP_BP / 1e4)
    n_tp = e * (1.0 + TP_BP / 1e4)
    ambigua = False

    for i in range(len(hm)):
        # ASIMETRIA DELIBERADA, y es la que hace la simulacion honesta:
        #
        #   - el STOP es una orden a mercado disparada por nivel. Si el open ya
        #     esta por debajo, rellena AHI, peor que el nivel. Es el hueco que
        #     la Fase 9 midio (deslizamiento maximo 54,1 bp, peor evento real
        #     -133,4 bp contra los -80 supuestos).
        #   - el TP es una orden LIMITE. Un hueco a favor no lo mejora: rellena
        #     en el nivel y punto. Darle el precio del open seria cobrar una
        #     mejora que el broker no da, y en la primera version de este script
        #     eso inflaba la media de los eventos con hueco favorable (16%).
        if o[i] <= n_sl:
            return (o[i] / e - 1.0) * 1e4, "stop_hueco", ambigua
        if o[i] >= n_tp:
            return TP_BP, "tp_hueco", ambigua

        toca_sl = l[i] <= n_sl
        toca_tp = h[i] >= n_tp
        if toca_sl and toca_tp:
            ambigua = True
            if orden_ambiguo == "stop":
                return -STOP_BP, "stop", ambigua
            return TP_BP, "tp", ambigua
        if toca_sl:
            return -STOP_BP, "stop", ambigua
        if toca_tp:
            return TP_BP, "tp", ambigua

    return (c[-1] / e - 1.0) * 1e4, "cierre_0930", ambigua


def hueco_maximo(ohlc, d_sal, d_ent):
    """Minutos del mayor agujero sin cotizacion dentro de la noche.

    La Fase 9 midio que 36 de 117 eventos tenian huecos de mas de 60 min y el
    mayor era de 240. Durante un agujero el stop NO puede ejecutarse, asi que
    un evento con agujero grande no es el mismo objeto que uno sin el.
    """
    s = senda(ohlc, d_ent, d_sal)
    if s is None or len(s[0]) < 2:
        return None
    hm = s[0]
    # el salto de fin de dia (23:59 -> 00:00) no es un agujero
    d = np.diff(hm)
    d = d[(d > 0)]
    return int(d.max()) if len(d) else 0


def tabla(res, etq):
    r = np.array([x[0] for x in res])
    mot = [x[1] for x in res]
    amb = sum(1 for x in res if x[2])
    n = len(r)
    cuenta = {k: mot.count(k) for k in sorted(set(mot))}
    print("  %-16s n=%3d  media %+7.2f bp  sd %5.1f  se %5.2f  peor %+7.1f"
          % (etq, n, r.mean(), r.std(ddof=1), r.std(ddof=1) / np.sqrt(n), r.min()))
    print("       motivos: %s"
          % " · ".join("%s %d (%.0f%%)" % (k, v, 100.0 * v / n)
                       for k, v in cuenta.items()))
    if amb:
        print("       barras ambiguas (stop y TP en la misma barra): %d de %d"
              % (amb, n))
    return r


def main():
    f = pd.read_csv(CSV_FECHAS, parse_dates=["fecha"])
    f = f[~f["fecha"].dt.strftime("%Y-%m-%d").isin(EXCLUIR)]
    fechas = set(f["fecha"].dt.date)

    print("pasada 1: dias de mercado validos (franja de contado) ...")
    mapas = mapas_por_dia(carga())
    todas = noches(mapas)
    ev = [(s, e) for s, e in todas if s in fechas]
    ct = [(s, e) for s, e in todas if s not in fechas and s.weekday() == 2]
    print("  noches pre-FOMC %d · noches de miercoles de control %d"
          % (len(ev), len(ct)))

    dias = set()
    for s, e in ev + ct:
        dias.add(s)
        dias.add(e)
    print("pasada 2: OHLC nocturno de %d dias ..." % len(dias))
    ohlc = carga_ohlc(dias)
    print("  dias con barras nocturnas: %d" % len(ohlc))

    print()
    print("=" * 84)
    print("CON TP %g bp Y STOP %g bp  ·  largo, como el EA" % (TP_BP, STOP_BP))
    print("=" * 84)

    out = {}
    for conv in ("stop", "tp"):
        r_ev = [z for z in (simula(ohlc, s, e, conv) for s, e in ev) if z]
        r_ct = [z for z in (simula(ohlc, s, e, conv) for s, e in ct) if z]
        print("\n  convencion en barra ambigua: %s primero"
              % ("el STOP" if conv == "stop" else "el TP"))
        x = tabla(r_ev, "pre-FOMC")
        y = tabla(r_ct, "control mie.")
        out[conv] = (x, y)
        print("       exceso: %+.2f bp" % (x.mean() - y.mean()))

    # ---------------------------------------------------- comparacion con bruto
    print()
    print("=" * 84)
    print("QUE CUESTA EL TP  ·  bruto contra con TP, mismos eventos")
    print("=" * 84)
    from ventana_nocturna import retorno
    xb = np.array([v for v in (retorno(mapas, s, e) for s, e in ev)
                   if v is not None])
    yb = np.array([v for v in (retorno(mapas, s, e) for s, e in ct)
                   if v is not None])
    print("  %-22s%12s%12s%12s" % ("", "pre-FOMC", "control", "exceso"))
    print("  " + "-" * 60)
    print("  %-22s%12.2f%12.2f%12.2f"
          % ("sin TP ni stop", xb.mean(), yb.mean(), xb.mean() - yb.mean()))
    for conv in ("stop", "tp"):
        x, y = out[conv]
        print("  %-22s%12.2f%12.2f%12.2f"
              % ("con TP/stop (%s 1o)" % conv, x.mean(), y.mean(),
                 x.mean() - y.mean()))

    # ---------------------------------------------------- robustez
    # Fase 7.5: "hay que comprobar siempre la version por rangos y la recortada
    # al 2%". Y el peor control de -428 bp pide mirar los agujeros de datos.
    print()
    print("=" * 84)
    print("ROBUSTEZ  ·  recorte al 2% y agujeros de cotizacion")
    print("=" * 84)
    x, y = out["stop"]

    def rec(v, p=2.0):
        lo, hi = np.percentile(v, [p, 100 - p])
        return v[(v >= lo) & (v <= hi)]

    print("  %-30s%11s%11s%11s" % ("", "pre-FOMC", "control", "exceso"))
    print("  " + "-" * 64)
    print("  %-30s%11.2f%11.2f%11.2f"
          % ("completo", x.mean(), y.mean(), x.mean() - y.mean()))
    xr, yr = rec(x), rec(y)
    print("  %-30s%11.2f%11.2f%11.2f"
          % ("recortado al 2%", xr.mean(), yr.mean(), xr.mean() - yr.mean()))
    print("  %-30s%11.2f%11.2f%11.2f"
          % ("mediana", np.median(x), np.median(y), np.median(x) - np.median(y)))

    hue_ev = [hueco_maximo(ohlc, s, e) for s, e in ev]
    hue_ct = [hueco_maximo(ohlc, s, e) for s, e in ct]
    hue_ev = np.array([h for h in hue_ev if h is not None])
    hue_ct = np.array([h for h in hue_ct if h is not None])
    print()
    print("  mayor agujero sin cotizacion dentro de la noche:")
    print("     pre-FOMC : mediana %3d min · p90 %3d · maximo %4d min"
          % (np.median(hue_ev), np.percentile(hue_ev, 90), hue_ev.max()))
    print("     control  : mediana %3d min · p90 %3d · maximo %4d min"
          % (np.median(hue_ct), np.percentile(hue_ct, 90), hue_ct.max()))

    UMBRAL = 60
    r_ev2 = [(z, h) for z, h in
             zip((simula(ohlc, s, e) for s, e in ev), hue_ev) if z]
    r_ct2 = [(z, h) for z, h in
             zip((simula(ohlc, s, e) for s, e in ct), hue_ct) if z]
    xe = np.array([z[0] for z, h in r_ev2 if h is not None and h <= UMBRAL])
    ye = np.array([z[0] for z, h in r_ct2 if h is not None and h <= UMBRAL])
    print()
    print("  solo noches con agujeros <= %d min:" % UMBRAL)
    print("     pre-FOMC n=%3d media %+.2f · control n=%3d media %+.2f"
          " · exceso %+.2f bp"
          % (len(xe), xe.mean(), len(ye), ye.mean(), xe.mean() - ye.mean()))
    print()
    print("  Si el exceso aguanta las cuatro filas, el efecto no lo sostienen")
    print("  ni las colas ni los agujeros de datos.")

    # ---------------------------------------------------- aleatorizacion
    print()
    print("=" * 84)
    print("ALEATORIZACION CON TP/STOP  ·  %d muestras" % N_MUESTRAS)
    print("=" * 84)
    rng = np.random.default_rng(SEMILLA)
    print("  %-14s%9s%9s%9s%9s%9s"
          % ("convencion", "FOMC", "nula", "exceso", "p emp.", "2se"))
    print("  " + "-" * 60)
    ale = {}
    for conv in ("stop", "tp"):
        x, y = out[conv]
        m = np.array([rng.choice(y, size=len(x), replace=False).mean()
                      for _ in range(N_MUESTRAS)])
        p = float((m >= x.mean()).mean())
        ale[conv] = (x.mean() - y.mean(), m.std(ddof=1), p)
        print("  %-14s%9.2f%9.2f%9.2f%9.4f%9.2f"
              % (conv + " 1o", x.mean(), y.mean(), x.mean() - y.mean(), p,
                 2 * m.std(ddof=1)))

    # ---------------------------------------------------- friccion y tamano
    bp_unidad = SWAP_ANUAL / UNID_ANIO * 1e4
    ida_vuelta = 2 * SPREAD_BP
    print()
    print("=" * 84)
    print("TAMANO DEFENDIBLE  ·  regla de la Fase 12.1, con el TP puesto")
    print("=" * 84)
    print("  ida y vuelta %.2f bp · una unidad de swap %.2f bp"
          % (ida_vuelta, bp_unidad))
    print()
    print("  %-16s%9s%7s%9s%9s%13s"
          % ("convencion", "exceso", "unid.", "friccion", "neto", "f defendible"))
    print("  " + "-" * 64)
    for conv in ("stop", "tp"):
        exceso, se, _ = ale[conv]
        for unid in (1, 3):
            fr = ida_vuelta + unid * bp_unidad
            neto = exceso - fr
            defend = neto - 2 * se
            print("  %-16s%9.2f%7d%9.2f%9.2f%13s"
                  % (conv + " 1o", exceso, unid, fr, neto,
                     "f = 0" if defend <= 0 else "%+.2f bp" % defend))

    # ---------------------------------------------------- el mejor dia
    print()
    print("=" * 84)
    print("EL MEJOR DIA  ·  la regla del 20% de la Fase 12")
    print("=" * 84)
    x, _ = out["stop"]
    CUENTA, RIESGO = 25000.0, 0.0110
    apal = RIESGO / (STOP_BP / 1e4)
    pnl = x / 1e4 * apal * CUENTA
    print("  apalancamiento = %.2f%% / %.0f bp = x%.3f" % (RIESGO * 100, STOP_BP, apal))
    print("  mejor dia         : %+.2f $" % pnl.max())
    print("  liston del 20%%    : %.2f $ de beneficio acumulado" % (pnl.max() * 5))
    print("  peor dia          : %+.2f $  (limite por operacion 2%% = %.0f $)"
          % (pnl.min(), CUENTA * 0.02))
    if abs(pnl.min()) > CUENTA * 0.02:
        print("       -> ROMPE el limite por operacion: hard breach")
    else:
        print("       -> dentro del limite, margen %.0f %%"
              % (100.0 * (1 - abs(pnl.min()) / (CUENTA * 0.02))))
    print("  dias que cualifican (>= +0,5%%): %d de %d (%.0f%%)"
          % (int((pnl >= CUENTA * 0.005).sum()), len(pnl),
             100.0 * (pnl >= CUENTA * 0.005).mean()))


if __name__ == "__main__":
    main()
