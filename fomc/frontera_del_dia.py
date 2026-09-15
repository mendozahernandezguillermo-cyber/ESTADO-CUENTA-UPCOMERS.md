#!/usr/bin/env python3
"""
¿ES LA ESTRATEGIA #1 SENSIBLE A LAS HORAS QUE ELEGI?

La especificacion dice: entrar a las 16:00 NY del dia de mercado anterior al
anuncio del FOMC y salir a las 09:30 NY del dia del anuncio. Esas dos horas las
elegi porque son el cierre y la apertura del contado, pero NUNCA comprobe si el
resultado depende de ellas.

Mi propio criterio de la Fase 7 dice que si la t oscila entre 0,4 y 3,4 segun
cambios triviales de especificacion, hay que parar. Esto es exactamente un
cambio trivial de especificacion.

PREDICCION REGISTRADA ANTES DE MIRAR
Ya medimos por separado que el efecto vive en el HUECO NOCTURNO y que la sesion
del dia del anuncio es NEGATIVA (-11,7 bp a las 11:00). Si eso es cierto:
  · alargar la salida mas alla de las 09:30 debe DEGRADAR de forma ordenada
  · adelantar la entrada debe meter ruido de la sesion previa, tambien de forma
    ordenada
  · la celda elegida debe estar en una MESETA, no en un pico aislado
Si en cambio el patron sale aleatorio, la estrategia esta ajustada a una hora
arbitraria y hay que pararla.

Se mide el retorno CRUDO (sin stop ni take profit) para aislar la pregunta de
la especificacion horaria de la del truncamiento.
"""
import os
import glob
import csv
import re
import datetime as dt
import numpy as np

DIR = "../nas100-data/raw"
VENTANA = 45          # minutos de tolerancia para encontrar precio

ENTRADAS = [(12, 0), (13, 0), (14, 0), (15, 0), (15, 30), (15, 57), (16, 0),
            (16, 30)]
SALIDAS = [(9, 30), (10, 0), (10, 30), (11, 0), (12, 0), (14, 0), (16, 0)]


def es_verano(u):
    a = u.year
    d = (dt.date(a, 3, 1).weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    d = (dt.date(a, 11, 1).weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano(u) else 5))


FECHAS = sorted(set(re.findall(
    r"\b(20\d{6})\b",
    open("../mql5/fechas_fomc_completas.txt", encoding="utf-8").read())))
interes = set()
for f in FECHAS:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

print("leyendo M1 ...")
# fecha NY -> {minuto del dia: cierre}
porminuto = {}
for path in sorted(glob.glob(os.path.join(DIR, "usatechidxusd-m1-*.csv"))):
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            try:
                ms = int(row[0])
                c = float(row[4])
            except (ValueError, IndexError):
                continue
            if c <= 0:
                continue
            ny = utc_a_ny(dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms))
            if ny.date() not in interes:
                continue
            porminuto.setdefault(ny.date(), {})[ny.hour * 60 + ny.minute] = c

# pares (dia de entrada, dia del anuncio)
PARES = []
for f in FECHAS:
    anuncio = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    if anuncio not in porminuto:
        continue
    ent = None
    for k in range(1, 5):
        cand = anuncio - dt.timedelta(days=k)
        if cand.weekday() < 5:
            ent = cand
            break
    if ent is None or ent not in porminuto:
        continue
    PARES.append((f, ent, anuncio))
print(f"eventos con datos M1: {len(PARES)}")


def precio(dia, minuto):
    """primer precio disponible desde 'minuto', hasta VENTANA minutos despues"""
    d = porminuto[dia]
    for m in range(minuto, minuto + VENTANA + 1):
        if m in d:
            return d[m]
    return None


def medir(h_ent, m_ent, h_sal, m_sal):
    rs = []
    for f, dia_e, dia_a in PARES:
        p1 = precio(dia_e, h_ent * 60 + m_ent)
        p2 = precio(dia_a, h_sal * 60 + m_sal)
        if p1 and p2:
            rs.append((p2 / p1 - 1.0) * 10000.0)
    if len(rs) < 30:
        return None
    a = np.array(rs)
    return dict(n=len(a), media=a.mean(),
                t=a.mean() / a.std(ddof=1) * np.sqrt(len(a)))


E = "=" * 92
print()
print(E)
print("REJILLA DE ESPECIFICACION: media en bp  /  estadistico t")
print(E)
print("  filas = hora de ENTRADA (dia previo)   ·   columnas = hora de SALIDA "
      "(dia del anuncio)")
print()
hdr = "  entrada  " + "".join(f"{f'{h:02d}:{m:02d}':>12}" for h, m in SALIDAS)
print(hdr)
print("  " + "-" * (len(hdr) - 2))
rejilla = {}
for h1, m1 in ENTRADAS:
    fila = f"  {h1:02d}:{m1:02d}    "
    for h2, m2 in SALIDAS:
        r = medir(h1, m1, h2, m2)
        rejilla[(h1, m1, h2, m2)] = r
        fila += (f"{r['media']:>+7.1f}/{r['t']:>4.2f}" if r else f"{'n/d':>12}")
    marca = "  <- la elegida" if (h1, m1) == (15, 57) else ""
    print(fila + marca)

vals = [v for v in rejilla.values() if v]
ts = np.array([v["t"] for v in vals])
ms = np.array([v["media"] for v in vals])
nuestra = rejilla[(15, 57, 9, 30)]

print()
print(E)
print("DIAGNOSTICO")
print(E)
print(f"  celdas medidas          : {len(vals)}")
print(f"  nuestra celda (15:57 -> 09:30) : {nuestra['media']:+.1f} bp  ·  "
      f"t = {nuestra['t']:.2f}  ·  n = {nuestra['n']}")
print()
print(f"  t: minimo {ts.min():.2f}  ·  mediana {np.median(ts):.2f}  ·  "
      f"maximo {ts.max():.2f}")
print(f"  celdas con t > 2        : {(ts > 2).sum()} de {len(ts)} "
      f"({(ts > 2).mean():.0%})")
print(f"  celdas con t > 3        : {(ts > 3).sum()} de {len(ts)}")
print(f"  celdas con media < 0    : {(ms < 0).sum()} de {len(ms)}")
print(f"  percentil de nuestra celda: {(ts < nuestra['t']).mean():.0%}")

# ---- ¿sigue el patron al mecanismo o es ruido?
print()
print(E)
print("¿LA VARIACION SIGUE EL MECANISMO O ES RUIDO?")
print(E)
print("  Prediccion registrada: alargar la salida degrada, porque la sesion del")
print("  dia del anuncio es negativa. Media por hora de SALIDA, promediando")
print("  todas las entradas:")
print()
print(f"  {'salida':>8}{'media bp':>12}{'t medio':>10}")
print("  " + "-" * 30)
for h2, m2 in SALIDAS:
    sub = [rejilla[(h1, m1, h2, m2)] for h1, m1 in ENTRADAS
           if rejilla[(h1, m1, h2, m2)]]
    print(f"  {f'{h2:02d}:{m2:02d}':>8}{np.mean([x['media'] for x in sub]):>+11.1f}"
          f"{np.mean([x['t'] for x in sub]):>10.2f}")

print()
print("  Media por hora de ENTRADA, promediando todas las salidas:")
print()
print(f"  {'entrada':>8}{'media bp':>12}{'t medio':>10}")
print("  " + "-" * 30)
for h1, m1 in ENTRADAS:
    sub = [rejilla[(h1, m1, h2, m2)] for h2, m2 in SALIDAS
           if rejilla[(h1, m1, h2, m2)]]
    print(f"  {f'{h1:02d}:{m1:02d}':>8}{np.mean([x['media'] for x in sub]):>+11.1f}"
          f"{np.mean([x['t'] for x in sub]):>10.2f}")

print()
print(E)
print("VEREDICTO CONTRA EL CRITERIO DE LA FASE 7")
print(E)
print("  El criterio dice PARAR si la t oscila entre 0,4 y 3,4 segun cambios")
print("  triviales de especificacion.")
print()
print(f"  rango observado: {ts.min():.2f} a {ts.max():.2f}")
print()
print("  Pero el criterio hay que leerlo con cuidado: lo que descalifica es la")
print("  oscilacion SIN MECANISMO. Si la degradacion sigue una direccion")
print("  predicha de antemano y por una razon medida por separado, es")
print("  confirmacion del mecanismo, no fragilidad. Las dos tablas de arriba")
print("  son las que deciden cual de las dos cosas es.")
