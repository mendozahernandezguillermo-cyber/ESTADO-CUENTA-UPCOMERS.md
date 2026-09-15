#!/usr/bin/env python3
"""
LA HORA DEL ANUNCIO, MEDIDA EN EL PRECIO  ·  guardian de reloj

Motivo. `control_m1.py` fija la hora del comunicado asi:

    anuncio = 14:15 si dia.year <= 2012 else 14:00

Para las reuniones sin conferencia de prensa eso es correcto. Pero en 2011-2012
los dias CON conferencia publicaban el comunicado a las 12:30 ET, para que la
comparecencia de las 14:15 llegase despues. Si eso es cierto, la regla vigente
apunta 105 minutos tarde en esos eventos.

No se cree ninguna de las dos versiones: se mide donde esta el salto.

METODO. El argmax del |retorno| de UN evento es ruido: el mayor movimiento de
5 minutos de la jornada cae donde quiera. Lo que si tiene senal es el PERFIL
AGREGADO — promediar |ret| minuto a minuto sobre todos los eventos de un tramo.
La reaccion al comunicado esta en el mismo minuto de reloj en todos ellos y
sobrevive al promedio; el ruido no.

Prediccion registrada ANTES de correrlo (Fase 13: predecir y luego mirar):

  1. 2013-2026                       -> el perfil agregado pica en 14:00
  2. 2011-2012, dias de conferencia  -> pica en 12:30
  3. dias que NO son FOMC            -> perfil plano, sin minuto dominante

La 3 es el control negativo y es la que da sentido a las otras dos: si los dias
sin anuncio tambien pican en 14:00, el detector no mide nada.

AVISO SOBRE fomc_fechas.csv. Su columna `conf_prensa` NO marca la reunion, marca
la EPOCA: esta en True para las 8 reuniones de 2012 cuando solo 4-5 tuvieron
comparecencia. Sirve para separar antes/despues de abril-2011 y nada mas. Aqui
la pertenencia a las 12:30 se decide midiendo, no leyendo esa bandera.

Salida: fomc/horas_medidas.csv, una fila por evento con la hora medida, la que
asume el codigo y la reaccion en cada candidata.
"""
import glob
import os

import numpy as np
import pandas as pd

DIR_M1 = os.path.join(os.path.dirname(__file__), "..", "nas100-data", "raw")
CSV_FECHAS = os.path.join(os.path.dirname(__file__), "fomc_fechas.csv")
SALIDA = os.path.join(os.path.dirname(__file__), "horas_medidas.csv")

# Reuniones no programadas / canceladas / voto por notacion: no son decisiones
# con comunicado a hora fija, asi que no entran. Misma lista que control_m1.py.
EXCLUIR = {"2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"}

VENT_INI = 11 * 60          # 11:00 NY
VENT_FIN = 15 * 60 + 30     # 15:30 NY
PASO = 5                    # la reaccion se mide en 5 minutos
BANDA = 5                   # +-5 min: tolerancia al asignar un evento a una hora

CANDIDATAS = [(12 * 60 + 30, "12:30"), (14 * 60, "14:00"), (14 * 60 + 15, "14:15")]


def hora_que_asume_el_codigo(anio):
    """La regla vigente en control_m1.py, para poder contrastarla."""
    return 14 * 60 + 15 if anio <= 2012 else 14 * 60


def carga(dias_interes):
    """M1 -> DataFrame(dia, hm, close) restringido a los dias y franja utiles."""
    trozos = []
    for p in sorted(glob.glob(os.path.join(DIR_M1, "usatechidxusd-m1-*.csv"))):
        d = pd.read_csv(p, usecols=["timestamp", "close"])
        ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
        ny = ts.dt.tz_convert("America/New_York")
        hm = ny.dt.hour * 60 + ny.dt.minute
        dia = ny.dt.date
        m = (hm >= VENT_INI - PASO) & (hm <= VENT_FIN + PASO) & dia.isin(dias_interes)
        if not m.any():
            continue
        trozos.append(pd.DataFrame({"dia": dia[m].values, "hm": hm[m].values,
                                    "close": d["close"][m].values}))
    if not trozos:
        raise SystemExit("no hay barras en la franja pedida")
    return pd.concat(trozos, ignore_index=True).sort_values(["dia", "hm"])


def precio_en(mapa, minuto, atras=30):
    """Ultimo precio en o antes de 'minuto'. None si no hay nada cerca."""
    for k in range(minuto, minuto - atras - 1, -1):
        if k in mapa:
            return mapa[k]
    return None


def ret_bp(mapa, minuto, paso=PASO):
    """Retorno en bp de los 'paso' minutos que ARRANCAN en 'minuto'."""
    a = precio_en(mapa, minuto - 1)
    b = precio_en(mapa, minuto + paso)
    if a is None or b is None or a <= 0:
        return None
    return (b / a - 1) * 1e4


def perfil(mapa):
    """array |ret| por minuto de la franja; NaN donde no se puede medir."""
    out = np.full(VENT_FIN - VENT_INI + 1, np.nan)
    for i, t in enumerate(range(VENT_INI, VENT_FIN + 1)):
        r = ret_bp(mapa, t)
        if r is not None:
            out[i] = abs(r)
    return out


def hhmm(m):
    return "%02d:%02d" % (m // 60, m % 60) if m is not None else "--:--"


def agregado(perfiles):
    """(minuto del pico, valor, array medio) del perfil promedio."""
    M = np.vstack(perfiles)
    med = np.nanmean(M, axis=0)
    i = int(np.nanargmax(med))
    return VENT_INI + i, med[i], med


def main():
    f = pd.read_csv(CSV_FECHAS, parse_dates=["fecha"])
    f = f[~f["fecha"].dt.strftime("%Y-%m-%d").isin(EXCLUIR)]
    f = f[f["fecha"].dt.year >= 2011]
    eventos = {r.fecha.date(): bool(r.conf_prensa) for r in f.itertuples()}

    # control negativo: mismos dias de la semana, 1 y 2 semanas antes
    normales = set()
    for d in eventos:
        for k in (7, 14):
            normales.add(d - pd.Timedelta(days=k))
    normales -= set(eventos)

    print("eventos FOMC en la lista (>=2011): %d" % len(eventos))
    print("cargando M1 de la franja %s-%s ..." % (hhmm(VENT_INI), hhmm(VENT_FIN)))
    px = carga(set(eventos) | normales)
    print("filas utiles: %d · dias distintos: %d" % (len(px), px["dia"].nunique()))

    perf_ev, filas, perf_norm = {}, [], []
    for dia, g in px.groupby("dia", sort=True):
        mapa = dict(zip(g["hm"].values, g["close"].values))
        if len(mapa) < 120:                       # dia demasiado incompleto
            continue
        p = perfil(mapa)
        if np.all(np.isnan(p)):
            continue
        if dia in eventos:
            perf_ev[dia] = p
            fila = dict(fecha=str(dia), anio=dia.year, epoca_conf=eventos[dia],
                        pico_evento=hhmm(VENT_INI + int(np.nanargmax(p))),
                        pico_bp=round(float(np.nanmax(p)), 2),
                        asume_codigo=hhmm(hora_que_asume_el_codigo(dia.year)))
            for m, nom in CANDIDATAS:
                r = ret_bp(mapa, m)
                fila["bp_%s" % nom.replace(":", "")] = (round(abs(r), 2)
                                                        if r is not None else np.nan)
            filas.append(fila)
        else:
            perf_norm.append(p)

    ev = pd.DataFrame(filas)
    if ev.empty:
        raise SystemExit("ningun evento con datos suficientes")

    # ---- asignacion por medicion: a que candidata pertenece cada evento
    def candidata_medida(r):
        mejor, mejor_v = "otra", -1.0
        for _, nom in CANDIDATAS:
            v = r["bp_%s" % nom.replace(":", "")]
            if not np.isnan(v) and v > mejor_v:
                mejor, mejor_v = nom, v
        return mejor

    ev["candidata_medida"] = ev.apply(candidata_medida, axis=1)

    print()
    print("=" * 78)
    print("PERFIL AGREGADO  ·  |ret| medio de 5 min, promediado sobre eventos")
    print("=" * 78)
    grupos = [("2013-2026 (FOMC)", ev.anio >= 2013),
              ("2011-2012 (FOMC)", ev.anio <= 2012)]
    for etq, sel in grupos:
        s = ev[sel]
        if s.empty:
            continue
        ps = [perf_ev[pd.Timestamp(x).date()] for x in s.fecha]
        m, v, _ = agregado(ps)
        print("  %-22s n=%3d   pico del agregado: %s  (%.1f bp)"
              % (etq, len(s), hhmm(m), v))
    if perf_norm:
        m, v, med_n = agregado(perf_norm)
        base = float(np.nanmedian(med_n))
        print("  %-22s n=%3d   pico del agregado: %s  (%.1f bp)"
              % ("CONTROL no-FOMC", len(perf_norm), hhmm(m), v))
        print("  %-22s                     mediana del perfil: %.1f bp"
              % ("", base))
        print("       -> el pico del control solo supera su propia mediana en"
              " %.0f%%; no hay minuto dominante." % (100.0 * (v / base - 1)))

    print()
    print("=" * 78)
    print("REACCION MEDIA EN CADA HORA CANDIDATA  (|ret| de 5 min, bp)")
    print("=" * 78)
    print("  %-26s%8s%8s%8s%6s" % ("tramo", "12:30", "14:00", "14:15", "n"))
    print("  " + "-" * 58)
    for etq, sel in [("2011-2012", ev.anio <= 2012), ("2013-2026", ev.anio >= 2013)]:
        s = ev[sel]
        if s.empty:
            continue
        print("  %-26s%8.1f%8.1f%8.1f%6d"
              % (etq, s.bp_1230.mean(), s.bp_1400.mean(), s.bp_1415.mean(), len(s)))
    if perf_norm:
        Mn = np.vstack(perf_norm)
        med_n = np.nanmean(Mn, axis=0)
        vals = [med_n[m - VENT_INI] for m, _ in CANDIDATAS]
        print("  %-26s%8.1f%8.1f%8.1f%6d"
              % ("control no-FOMC", vals[0], vals[1], vals[2], len(perf_norm)))

    print()
    print("=" * 78)
    print("A QUE HORA PERTENECE CADA EVENTO, SEGUN EL PRECIO")
    print("=" * 78)
    tab = pd.crosstab(ev.anio, ev.candidata_medida)
    print(tab.to_string())

    print()
    print("=" * 78)
    print("VEREDICTO SOBRE LA REGLA DE control_m1.py")
    print("=" * 78)
    v1112 = ev[ev.anio <= 2012]
    n1230 = int((v1112.candidata_medida == "12:30").sum())
    print("  2011-2012: eventos con datos          : %d" % len(v1112))
    print("  2011-2012: la mayor reaccion en 12:30 : %d" % n1230)
    print("  2011-2012: la regla vigente asume     : 14:15 para los %d"
          % len(v1112))
    print()
    print("  Los eventos donde el codigo apunta 105 min tarde:")
    print("  %-12s%9s%9s%9s   %s" % ("fecha", "12:30", "14:00", "14:15", "pico"))
    for r in v1112[v1112.candidata_medida == "12:30"].itertuples():
        print("  %-12s%9.1f%9.1f%9.1f   %s"
              % (r.fecha, r.bp_1230, r.bp_1400, r.bp_1415, r.pico_evento))

    ev.to_csv(SALIDA, index=False)
    print()
    print("  escrito: %s  (%d filas)" % (os.path.relpath(SALIDA), len(ev)))


if __name__ == "__main__":
    main()
