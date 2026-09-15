#!/usr/bin/env python3
"""
EL LIMITE DIARIO SE FOTOGRAFIA CON LA POSICION DEL FOMC ABIERTA.

La documentacion de Upcomers dice que la base del limite diario es el MAYOR de
(equity, saldo) a las 00:00 UTC. La estrategia #1 abre a las 15:57 NY y cierra
a las 09:30 NY del dia siguiente, asi que las 00:00 UTC caen EN MEDIO de la
tenencia: a las 20:00 NY en verano y a las 19:00 en invierno.

Consecuencia, que es el ejemplo 2 de su propia documentacion: si a esa hora la
posicion va en BENEFICIO, la base se fija sobre la equity inflada. Si luego se
gira, puedes romper el limite diario del 4% habiendo terminado el dia plano.

Ninguna de mis simulaciones capturaba esto: todas usaban el saldo al inicio
del dia, no el maximo de saldo y equity a medianoche UTC.

Se mide sobre los 117 eventos con datos M1 reales:
  · retorno acumulado en el instante de la foto
  · base = 1 + max(0, retorno_foto x apalancamiento)
  · peor equity entre la foto y la salida, con relleno real del stop
  · caida desde la base, que es lo que la firma compara contra el 4%
"""
import os
import glob
import csv
import datetime as dt
import re

DIR = "../nas100-data/raw"
STOP_BP, TP_BP = 80.0, 80.0
MIN_ANTES, VENTANA_MIN = 3, 45
LIMITE_DIARIO = 4.0          # %


def es_verano_eeuu(u):
    a = u.year
    d = (dt.date(a, 3, 1).weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    d = (dt.date(a, 11, 1).weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano_eeuu(u) else 5))


FECHAS = sorted(set(re.findall(r"\b(20\d{6})\b",
                open("fechas_fomc_completas.txt", encoding="utf-8").read())))
interes = set()
for f in FECHAS:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

print("leyendo M1 ...")
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
                o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
            except (ValueError, IndexError):
                continue
            if c <= 0:
                continue
            # se guarda tambien el UTC para localizar la medianoche exacta
            barras.setdefault(ny.date(), []).append((ny, u, o, h, l, c))
for k in barras:
    barras[k].sort()

filas = []
for f in FECHAS:
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

    ini_m, fin_m = 16 * 60 - MIN_ANTES, 16 * 60 + VENTANA_MIN
    entrada = None
    for b in barras[ent_dia]:
        m = b[0].hour * 60 + b[0].minute
        if ini_m <= m <= fin_m:
            entrada = b
            break
    if entrada is None:
        continue
    t_ent, u_ent, _, _, _, p_ent = entrada
    sl = p_ent * (1 - STOP_BP / 10000.0)
    tp = p_ent * (1 + TP_BP / 10000.0)

    seq = [b for b in barras[ent_dia] if b[0] > t_ent] + \
          [b for b in barras[anuncio]
           if (b[0].hour * 60 + b[0].minute) <= 9 * 60 + 30]
    if not seq:
        continue

    # --- recorrer hasta la salida, guardando la foto de medianoche UTC
    r_foto = None
    peor_post = None
    salida = None
    for (ny, u, o, h, l, c) in seq:
        # foto: primera barra cuyo UTC ya paso de medianoche
        if r_foto is None and u.hour == 0 and u.minute == 0:
            r_foto = c / p_ent - 1.0
        if r_foto is not None:
            r_l = l / p_ent - 1.0
            peor_post = r_l if peor_post is None else min(peor_post, r_l)
        if l <= sl:
            p_sal = o if o <= sl else sl        # relleno real
            salida = ("stop", p_sal)
            break
        if h >= tp:
            salida = ("take profit", tp)
            break
    if salida is None:
        salida = ("hora 09:30", seq[-1][5])
    if r_foto is None:
        continue          # no hubo cotizacion en la medianoche UTC

    r_final = salida[1] / p_ent - 1.0
    # el peor punto desde la foto no puede ser mejor que el resultado final
    if peor_post is None:
        peor_post = r_final
    peor_post = min(peor_post, r_final)
    filas.append(dict(ev=f, r_foto=r_foto, peor=peor_post, r_fin=r_final,
                      motivo=salida[0]))

E = "=" * 86
print()
print(E)
print(f"CAIDA DESDE LA FOTO DE MEDIANOCHE UTC  ·  {len(filas)} eventos con datos")
print(E)


def analizar(apal, riesgo):
    peor_dd, rompen, detalles = 0.0, 0, []
    for x in filas:
        base = 1.0 + max(0.0, x["r_foto"] * apal)
        eq_min = 1.0 + x["peor"] * apal
        dd = (eq_min / base - 1.0) * 100.0
        detalles.append((dd, x))
        if dd < -LIMITE_DIARIO:
            rompen += 1
        peor_dd = min(peor_dd, dd)
    detalles.sort(key=lambda z: z[0])
    return peor_dd, rompen, detalles


print(f"  {'riesgo':>8}{'apalanc':>9}{'peor caida':>13}{'% del 4%':>11}"
      f"{'eventos que rompen':>21}")
print("  " + "-" * 62)
for riesgo in (2.14, 1.35, 1.00, 0.80):
    apal = riesgo / (STOP_BP / 100.0)
    peor, rompen, det = analizar(apal, riesgo)
    marca = "  <- coherente" if abs(riesgo - 1.35) < 1e-9 else ""
    print(f"  {riesgo:>7.2f}%{apal:>9.3f}{peor:>12.2f}%"
          f"{abs(peor)/LIMITE_DIARIO*100:>10.0f}%{rompen:>13} de {len(filas)}"
          f"{marca}")

print()
apal = 1.35 / 0.80
peor, rompen, det = analizar(apal, 1.35)
print("  LOS CINCO PEORES EVENTOS con el riesgo coherente (1,35%):")
print(f"     {'evento':<10}{'ret a medianoche':>18}{'peor punto':>13}"
      f"{'caida desde base':>19}{'salida':>14}")
for dd, x in det[:5]:
    print(f"     {x['ev']:<10}{x['r_foto']*10000:>+15.0f} bp"
          f"{x['peor']*10000:>+11.0f} bp{dd:>17.2f}%{x['motivo']:>14}")

print()
print("  CUANTAS VECES LA FOTO SALE INFLADA (posicion en beneficio):")
inflada = sum(1 for x in filas if x["r_foto"] > 0)
print(f"     {inflada} de {len(filas)}  ({inflada/len(filas):.0%})")
med = sorted(x["r_foto"] for x in filas)
print(f"     retorno mediano a medianoche: {med[len(med)//2]*10000:+.0f} bp")
print(f"     maximo:                       {med[-1]*10000:+.0f} bp")

print()
print(E)
print("EFECTO DE LA FOTO: comparar con medir desde el saldo del dia anterior")
print(E)
print("  Asi lo modelaban todas mis simulaciones (base = saldo, sin inflar):")
print(f"  {'riesgo':>8}{'peor caida con foto':>22}{'peor caida sin foto':>22}"
      f"{'diferencia':>13}")
print("  " + "-" * 65)
for riesgo in (2.14, 1.35, 1.00):
    apal = riesgo / 0.80
    con, _, _ = analizar(apal, riesgo)
    sin = min((1.0 + x["peor"] * apal) / 1.0 - 1.0 for x in filas) * 100.0
    print(f"  {riesgo:>7.2f}%{con:>21.2f}%{sin:>21.2f}%{con - sin:>12.2f}%")
print()
print("  La diferencia es lo que mis simulaciones NO veian.")
