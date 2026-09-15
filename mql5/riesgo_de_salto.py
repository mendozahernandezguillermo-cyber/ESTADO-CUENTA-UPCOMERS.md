#!/usr/bin/env python3
"""
¿PUEDE EL PRECIO SALTARSE EL STOP?

Todo lo que he simulado del EA #1 supone que el stop se ejecuta a -80 bp.
Bajo ese supuesto, la peor operacion posible cuesta 80 bp x 2,67 = 2,14% de
la equity y el Guardian nunca hace falta para eso.

Pero el peor evento historico del FOMC en el indice de CONTADO fue de
-422,6 bp. Si eso llegase de un salto, costaria -11,3% de la equity y
liquidaria la cuenta de 50K sin que nada pudiera evitarlo: ni el stop, ni el
factor de tamaño, ni el Guardian.

La pregunta no es cuanto se movio el indice: es si el CFD COTIZO durante ese
movimiento. Si cotizo, el stop se ejecuta a -80 bp y no pasa nada. Si hubo
un hueco sin cotizacion, el stop se ejecuta al primer precio disponible, que
puede estar mucho mas abajo.

Este script mide, sobre los M1 reales de Dukascopy y para cada evento:

  1. el precio REAL al que se habria ejecutado el stop:
       - si la barra que toca el stop ABRE ya por debajo, el precio salto y
         el relleno es la apertura de esa barra, peor que el stop;
       - si abre por encima, el precio paso por el stop cotizando y el
         relleno es el stop.
  2. el mayor salto de un minuto al siguiente durante la tenencia, medido
     como la apertura de una barra contra el cierre de la anterior.
  3. los minutos SIN COTIZACION dentro de la tenencia, que son los huecos
     en que un stop no puede ejecutarse.
"""
import os
import glob
import csv
import datetime as dt
import re
from collections import Counter

DIR = "../nas100-data/raw"
STOP_BP = 80.0
TP_BP = 80.0
MIN_ANTES = 3
VENTANA_MIN = 45
LEV = 2.67          # apalancamiento con InpRiesgoPorEvento = 2,14 y stop 80 bp


def cargar_fechas():
    txt = open("fechas_fomc_completas.txt", encoding="utf-8").read()
    return sorted(set(re.findall(r"\b(20\d{6})\b", txt)))


def es_verano_eeuu(u):
    a = u.year
    d = (dt.date(a, 3, 1).weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    d = (dt.date(a, 11, 1).weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano_eeuu(u) else 5))


print("leyendo M1 de Dukascopy ...")
FECHAS_EV = cargar_fechas()
interes = set()
for f in FECHAS_EV:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

barras = {}
for path in sorted(glob.glob(os.path.join(DIR, "usatechidxusd-m1-*.csv"))):
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            try:
                ms = int(row[0])
            except (ValueError, IndexError):
                continue
            u = dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms)
            ny = utc_a_ny(u)
            if ny.date() not in interes:
                continue
            try:
                o, h, l, c = (float(row[1]), float(row[2]),
                              float(row[3]), float(row[4]))
            except (ValueError, IndexError):
                continue
            if c <= 0:
                continue
            barras.setdefault(ny.date(), []).append((ny, o, h, l, c))
for k in barras:
    barras[k].sort()

filas = []
for f in FECHAS_EV:
    anuncio = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    if anuncio not in barras:
        continue
    ent_dia = None
    for k in range(1, 5):
        cand = anuncio - dt.timedelta(days=k)
        if cand.weekday() >= 5:
            continue
        ent_dia = cand
        break
    if ent_dia is None or ent_dia not in barras:
        continue

    ini_min = 16 * 60 - MIN_ANTES
    fin_min = 16 * 60 + VENTANA_MIN
    entrada = None
    for (t, o, h, l, c) in barras[ent_dia]:
        m = t.hour * 60 + t.minute
        if ini_min <= m <= fin_min:
            entrada = (t, c)
            break
    if entrada is None:
        continue
    t_ent, p_ent = entrada
    sl = p_ent * (1.0 - STOP_BP / 10000.0)
    tp = p_ent * (1.0 + TP_BP / 10000.0)

    seq = [b for b in barras[ent_dia] if b[0] > t_ent] + \
          [b for b in barras[anuncio]
           if (b[0].hour * 60 + b[0].minute) <= 9 * 60 + 30]
    if not seq:
        continue

    # --- huecos de cotizacion y saltos de un minuto al siguiente
    minutos_teoricos = int((seq[-1][0] - t_ent).total_seconds() // 60)
    sin_cotizar = max(minutos_teoricos - len(seq), 0)
    peor_salto = 0.0
    hueco_max = 0
    prev_t, prev_c = t_ent, p_ent
    for (t, o, h, l, c) in seq:
        salto = (o / prev_c - 1.0) * 10000.0
        if salto < peor_salto:
            peor_salto = salto
        gap = int((t - prev_t).total_seconds() // 60) - 1
        if gap > hueco_max:
            hueco_max = gap
        prev_t, prev_c = t, c

    # --- relleno REAL del stop
    motivo, p_sal, deslizamiento = "", None, 0.0
    for (t, o, h, l, c) in seq:
        if l <= sl:
            if o <= sl:
                p_sal = o                       # la barra ABRE por debajo
                deslizamiento = (sl / o - 1.0) * 10000.0
            else:
                p_sal = sl                      # cotizo a traves del stop
            motivo = "stop"
            break
        if h >= tp:
            p_sal, motivo = tp, "take profit"
            break
    if p_sal is None:
        p_sal, motivo = seq[-1][4], "hora 09:30"

    filas.append(dict(ev=f, r_ideal=None, motivo=motivo,
                      r=(p_sal / p_ent - 1.0) * 10000.0,
                      desliz=deslizamiento, peor_salto=peor_salto,
                      sin_cotizar=sin_cotizar, hueco_max=hueco_max,
                      minutos=len(seq)))

E = "=" * 84
print()
print(E)
print("RIESGO DE SALTO DEL STOP  ·  %d eventos con datos M1" % len(filas))
print(E)

print("\n  reparto de salidas:")
for k, v in Counter(x["motivo"] for x in filas).most_common():
    print("     %-14s %3d" % (k, v))

stops = [x for x in filas if x["motivo"] == "stop"]
print("\n  DE LOS %d STOPS EJECUTADOS:" % len(stops))
con_desliz = [x for x in stops if x["desliz"] > 0.001]
print("     ejecutados exactamente a -80 bp     : %d" % (len(stops) - len(con_desliz)))
print("     ejecutados PEOR que -80 bp (salto)  : %d" % len(con_desliz))
if con_desliz:
    peor = max(con_desliz, key=lambda x: x["desliz"])
    print("     deslizamiento maximo                : %.1f bp (evento %s)"
          % (peor["desliz"], peor["ev"]))
    print("     deslizamiento medio cuando ocurre   : %.1f bp"
          % (sum(x["desliz"] for x in con_desliz) / len(con_desliz)))

print("\n  PEOR RESULTADO REAL DE UN EVENTO:")
peor_ev = min(filas, key=lambda x: x["r"])
print("     %+.1f bp   (evento %s, salida por %s)"
      % (peor_ev["r"], peor_ev["ev"], peor_ev["motivo"]))
print("     coste en equity con apalancamiento x%.2f : %.2f%%"
      % (LEV, peor_ev["r"] * LEV / 100.0))

print("\n  SALTOS DE UN MINUTO AL SIGUIENTE durante la tenencia:")
saltos = sorted(x["peor_salto"] for x in filas)
print("     peor salto de todos                 : %.1f bp" % saltos[0])
print("     mediana del peor salto por evento   : %.1f bp"
      % saltos[len(saltos) // 2])
print("     eventos con algun salto peor de -80 : %d de %d"
      % (sum(1 for s in saltos if s < -80.0), len(saltos)))
print("     eventos con algun salto peor de -40 : %d de %d"
      % (sum(1 for s in saltos if s < -40.0), len(saltos)))

print("\n  MINUTOS SIN COTIZACION dentro de la tenencia:")
huecos = sorted((x["hueco_max"] for x in filas), reverse=True)
print("     hueco continuo mas largo            : %d minutos" % huecos[0])
print("     mediana del hueco mas largo         : %d minutos"
      % huecos[len(huecos) // 2])
print("     eventos con un hueco de mas de 60 min: %d de %d"
      % (sum(1 for h in huecos if h > 60), len(huecos)))
print("     minutos cotizados por evento (media): %.0f de %.0f teoricos"
      % (sum(x["minutos"] for x in filas) / len(filas),
         sum(x["minutos"] + x["sin_cotizar"] for x in filas) / len(filas)))

print("\n  LOS CINCO PEORES EVENTOS POR RESULTADO REAL:")
print("     %-10s %10s %12s %12s %10s" %
      ("evento", "result bp", "desliz bp", "peor salto", "% equity"))
for x in sorted(filas, key=lambda z: z["r"])[:5]:
    print("     %-10s %+10.1f %12.1f %12.1f %9.2f%%"
          % (x["ev"], x["r"], x["desliz"], x["peor_salto"], x["r"] * LEV / 100.0))
