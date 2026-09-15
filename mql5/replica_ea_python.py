#!/usr/bin/env python3
"""
CONTROL POSITIVO DEL CODIGO DEL EA.

Replica en Python la logica EXACTA del EA_FOMC_Gap y la corre sobre los datos
M1 de Dukascopy (2011-2026, ~120 eventos). Si el resultado coincide con la
medicion original, la logica del EA es fiel. Si no coincide, hay un sexto bug.

Se replica todo lo que el EA hace, incluidos los detalles que se anadieron a
raiz de los bugs:
  - entrada 3 minutos ANTES de las 16:00 NY (por el hueco de cotizacion)
  - ventana de entrada de 45 minutos tras la hora objetivo
  - salida a las 09:30 NY del dia del anuncio
  - stop en -80 bp y take profit en +80 bp, comprobados vela a vela
  - hora de NY calculada desde UTC con las reglas de horario de verano

SUPUESTO CONSERVADOR: si en el mismo minuto se tocan el stop y el take
profit, se asume que salto el STOP. Es el peor caso y evita inflar el
resultado con una ambiguedad que no se puede resolver con datos M1.

Los datos de Dukascopy estan en UTC, asi que aqui no hay offset de broker.
"""
import os
import glob
import csv
import datetime as dt

DIR = "../nas100-data/raw"
STOP_BP = 80.0
TP_BP = 80.0
MIN_ANTES = 3
VENTANA_MIN = 45

# fechas de anuncio del FOMC embebidas en el EA
FECHAS = """
20000202 20000321 20000516 20000628 20000822 20001003 20001115 20001219
""".split()


def cargar_fechas():
    """lee las 212 fechas historicas del fichero generado para el EA"""
    p = "fechas_fomc_completas.txt"
    txt = open(p, encoding="utf-8").read()
    import re
    return sorted(set(re.findall(r"\b(20\d{6})\b", txt)))


def es_verano_eeuu(u):
    """replica de EsVeranoEEUU() del EA"""
    a = u.year
    m1 = dt.date(a, 3, 1)
    d = (m1.weekday() + 1) % 7
    ini = dt.datetime(a, 3, 1 + ((7 - d) % 7) + 7, 7, 0)
    n1 = dt.date(a, 11, 1)
    d = (n1.weekday() + 1) % 7
    fin = dt.datetime(a, 11, 1 + ((7 - d) % 7), 6, 0)
    return ini <= u < fin


def utc_a_ny(u):
    return u - dt.timedelta(hours=(4 if es_verano_eeuu(u) else 5))


# ------------------------------------------------- cargar M1 por dias
print("leyendo M1 de Dukascopy ...")
FECHAS_EV = cargar_fechas()
# solo interesan los dias cercanos a cada evento
interes = set()
for f in FECHAS_EV:
    d = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    for k in range(-4, 1):
        interes.add(d + dt.timedelta(days=k))

barras = {}          # fecha NY -> lista de (datetime NY, o, h, l, c)
n_leidas = 0
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
            n_leidas += 1
for k in barras:
    barras[k].sort()
print("barras utiles: %d en %d dias" % (n_leidas, len(barras)))

# ------------------------------------------------- simular el EA
dias_con_datos = sorted(barras.keys())
resultados = []
sin_datos = 0
sin_entrada = 0

for f in FECHAS_EV:
    anuncio = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
    if anuncio not in barras:
        sin_datos += 1
        continue
    # dia de mercado anterior segun la logica del EA: el dia de semana previo
    ent_dia = None
    for k in range(1, 5):
        cand = anuncio - dt.timedelta(days=k)
        if cand.weekday() >= 5:
            continue
        ent_dia = cand
        break
    if ent_dia is None or ent_dia not in barras:
        sin_datos += 1
        continue

    # ---- ENTRADA: primer precio desde 15:57 hasta 16:45 NY
    ini_min = 16 * 60 - MIN_ANTES
    fin_min = 16 * 60 + VENTANA_MIN
    entrada = None
    for (t, o, h, l, c) in barras[ent_dia]:
        m = t.hour * 60 + t.minute
        if ini_min <= m <= fin_min:
            entrada = (t, c)
            break
    if entrada is None:
        sin_entrada += 1
        continue
    t_ent, p_ent = entrada
    sl = p_ent * (1.0 - STOP_BP / 10000.0)
    tp = p_ent * (1.0 + TP_BP / 10000.0)

    # ---- GESTION: desde la entrada hasta las 09:30 NY del anuncio
    salida = None
    motivo = ""
    secuencia = [b for b in barras[ent_dia] if b[0] > t_ent] + \
                [b for b in barras[anuncio]
                 if (b[0].hour * 60 + b[0].minute) <= 9 * 60 + 30]
    for (t, o, h, l, c) in secuencia:
        toca_sl = (l <= sl)
        toca_tp = (h >= tp)
        if toca_sl:                      # conservador: el stop manda
            salida, motivo = (t, sl), "stop"
            break
        if toca_tp:
            salida, motivo = (t, tp), "take profit"
            break
    if salida is None:
        if secuencia:
            t_s, _, _, _, c_s = secuencia[-1]
            salida, motivo = (t_s, c_s), "hora 09:30"
        else:
            sin_entrada += 1
            continue

    t_sal, p_sal = salida
    r_bp = (p_sal / p_ent - 1.0) * 10000.0
    resultados.append(dict(evento=f, t_ent=t_ent, p_ent=p_ent,
                           t_sal=t_sal, p_sal=p_sal, r=r_bp, motivo=motivo))

# ------------------------------------------------- informe
print()
print("=" * 84)
print("RESULTADO DE LA REPLICA DEL EA SOBRE DUKASCOPY M1")
print("=" * 84)
print("eventos en la tabla del EA      : %d" % len(FECHAS_EV))
print("eventos sin datos M1 (pre-2011) : %d" % sin_datos)
print("eventos sin entrada posible     : %d" % sin_entrada)
print("eventos OPERADOS                : %d" % len(resultados))

if not resultados:
    raise SystemExit("sin resultados")

rs = [x["r"] for x in resultados]
n = len(rs)
media = sum(rs) / n
var = sum((x - media) ** 2 for x in rs) / (n - 1)
sd = var ** 0.5
t = media / (sd / n ** 0.5)
print()
print("  media por evento : %+.2f bp" % media)
print("  desviacion       : %.2f bp" % sd)
print("  t                : %.2f" % t)
print("  %% positivos       : %.1f%%" % (100.0 * sum(1 for x in rs if x > 0) / n))

from collections import Counter
print()
print("  reparto de salidas:")
for k, v in Counter(x["motivo"] for x in resultados).most_common():
    print("     %-14s %3d  (%.0f%%)" % (k, v, 100.0 * v / n))

print()
print("  hora de entrada (NY):")
for k, v in Counter(x["t_ent"].strftime("%H:%M")
                    for x in resultados).most_common(6):
    print("     %s  %3d" % (k, v))

print()
print("=" * 84)
print("CONTRASTE CON LA MEDICION ORIGINAL")
print("=" * 84)
print("  medicion en Python sin truncar (212 eventos) : +18,4 bp")
print("  medicion truncando a +-80 bp                 : +14,9 bp")
print("  replica del EA aqui (%d eventos)             : %+.2f bp" % (n, media))
dif = abs(media - 14.9)
print()
if dif < 6.0:
    print("  -> COMPATIBLE. La logica del EA reproduce la medicion.")
else:
    print("  -> DISCREPA en %.1f bp. Hay que entender por que antes de operar."
          % dif)
print()
print("  Nota: no es esperable que coincida al decimal. La replica usa la")
print("  ventana de entrada real (15:57-16:45), comprueba el stop vela a vela")
print("  y asume el peor caso cuando stop y take profit se tocan en el mismo")
print("  minuto. La medicion original usaba el cierre exacto de las 16:00.")
