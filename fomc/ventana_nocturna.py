#!/usr/bin/env python3
"""
LA VENTANA QUE OPERA EL EA, MEDIDA CONTRA CONTROLES EMPAREJADOS

Que se mide. La configuracion viva de EA_FOMC_Gap segun ESTADO-CUENTA:

    entrada : 15:57 NY del dia ANTERIOR al anuncio  (InpHoraEntradaNY 16:00,
              InpMinutosAntes 3)
    salida  : 09:30 NY del dia DEL anuncio          (InpHoraSalidaNY 09:30)

O sea una tenencia nocturna de ~17,5 h. No es la ventana que mide
`control_m1.py` — esa va de 09:30 al anuncio, dentro del mismo dia, y su propia
prediccion pre-registrada quedo REFUTADA (t=-0,57 en 2011-2015). Son dos cosas
distintas y conviene no confundirlas: aqui se mide la nocturna, que es la que
tiene dinero real dentro.

Por que hace falta un control. El retorno nocturno no es cero en general: los
indices tienen prima overnight. Medir +20 bp en las noches pre-FOMC no dice
nada si TODAS las noches dan +20 bp. La Fase 5.2 lo resuelve con controles
emparejados, y aqui el emparejamiento tiene que ser por DIA DE LA SEMANA,
porque el FOMC decide en miercoles y la noche del martes no es una noche
cualquiera (rollover triple, ver mas abajo).

Tres controles, de mas debil a mas fuerte:
  A) todas las noches del historico
  B) solo las noches del mismo dia de la semana que el evento
  C) las noches del mismo dia de la semana a -7 y -14 dias del evento

Prediccion registrada ANTES de correrlo:
  1. si el efecto es real, supera al control C con t>2 en la muestra completa
  2. el perfil por tramos decae (la literatura da el efecto por muerto tras 2015)
  3. el signo NO cambia al mover la hora de entrada o de salida una franja
     (criterio de parada de la Fase 6: se cuentan cambios de signo)

AVISO SOBRE LA FRICCION, que no es la que esta presupuestada. El anuncio es en
miercoles, la entrada cae el martes por la tarde y el rollover del swap es a las
00:00 del servidor = 18:00 NY. Asi que la posicion cruza el rollover que sella
el miercoles, y ese cobra TRIPLE. La tenencia paga 3 unidades de swap por
evento, no 1. ESTADO-CUENTA presupuesta "50 $/año (8 noches)"; con 3 unidades
son ~145 $/año. Es el error que la propia Fase 15 manda no cometer ("cuenta
unidades de swap, no noches") aplicado a la unica pata que queda viva.
`friccion_evento.py` lo tabula.
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy import stats

DIR_M1 = os.path.join(os.path.dirname(__file__), "..", "nas100-data", "raw")
CSV_FECHAS = os.path.join(os.path.dirname(__file__), "fomc_fechas.csv")

EXCLUIR = {"2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"}

HM_INI = 9 * 60             # 09:00 NY
HM_FIN = 16 * 60 + 30       # 16:30 NY
MIN_BARRAS = 200            # un dia con menos barras utiles no es dia completo

ENTRADA = 15 * 60 + 57      # 15:57 NY, la configuracion viva
SALIDA = 9 * 60 + 30        # 09:30 NY

# rejilla de robustez: no se elige la mejor celda, se cuentan cambios de signo
ENTRADAS = [(15 * 60, "15:00"), (15 * 60 + 30, "15:30"),
            (15 * 60 + 57, "15:57"), (16 * 60 + 15, "16:15")]
SALIDAS = [(9 * 60 + 30, "09:30"), (9 * 60 + 45, "09:45"),
           (10 * 60 + 30, "10:30"), (12 * 60, "12:00")]


def carga():
    trozos = []
    for p in sorted(glob.glob(os.path.join(DIR_M1, "usatechidxusd-m1-*.csv"))):
        d = pd.read_csv(p, usecols=["timestamp", "close"])
        ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
        ny = ts.dt.tz_convert("America/New_York")
        hm = ny.dt.hour * 60 + ny.dt.minute
        m = (hm >= HM_INI) & (hm <= HM_FIN)
        trozos.append(pd.DataFrame({"dia": ny.dt.date[m].values,
                                    "hm": hm[m].values,
                                    "close": d["close"][m].values}))
    return pd.concat(trozos, ignore_index=True).sort_values(["dia", "hm"])


def mapas_por_dia(px):
    """dia -> {minuto: cierre}, solo dias con suficientes barras."""
    out = {}
    for dia, g in px.groupby("dia", sort=True):
        if len(g) < MIN_BARRAS:
            continue
        out[dia] = dict(zip(g["hm"].values, g["close"].values))
    return out


def precio_en(mapa, minuto, atras=45):
    for k in range(minuto, minuto - atras - 1, -1):
        if k in mapa:
            return mapa[k]
    return None


def noches(mapas):
    """Lista de (dia_salida, dia_entrada) de noches consecutivas de mercado."""
    dias = sorted(mapas)
    return [(dias[i], dias[i - 1]) for i in range(1, len(dias))]


def retorno(mapas, d_sal, d_ent, m_ent=ENTRADA, m_sal=SALIDA):
    a = precio_en(mapas[d_ent], m_ent)
    b = precio_en(mapas[d_sal], m_sal)
    if a is None or b is None or a <= 0:
        return None
    return (b / a - 1) * 1e4


def resumen(x):
    x = np.asarray([v for v in x if v is not None])
    if len(x) < 2:
        return dict(n=len(x), media=np.nan, sd=np.nan, se=np.nan)
    return dict(n=len(x), media=x.mean(), sd=x.std(ddof=1),
                se=x.std(ddof=1) / np.sqrt(len(x)))


def main():
    f = pd.read_csv(CSV_FECHAS, parse_dates=["fecha"])
    f = f[~f["fecha"].dt.strftime("%Y-%m-%d").isin(EXCLUIR)]
    fechas = set(f["fecha"].dt.date)

    print("cargando M1 ...")
    px = carga()
    mapas = mapas_por_dia(px)
    print("dias de mercado utilizables: %d · %s -> %s"
          % (len(mapas), min(mapas), max(mapas)))

    todas = noches(mapas)
    ev = [(s, e) for s, e in todas if s in fechas]
    print("noches totales: %d · noches pre-FOMC con datos: %d"
          % (len(todas), len(ev)))

    dow = {}
    for s, e in ev:
        dow[s.weekday()] = dow.get(s.weekday(), 0) + 1
    nom_dow = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
    print("dia de la semana del anuncio: %s"
          % ", ".join("%s=%d" % (nom_dow[k], v) for k, v in sorted(dow.items())))

    # controles
    set_ev = set(ev)
    ctrl_A = [(s, e) for s, e in todas if (s, e) not in set_ev]
    ctrl_B = [(s, e) for s, e in ctrl_A if s.weekday() == 2]      # miercoles
    fechas_ct = set()
    for s, _ in ev:
        for k in (7, 14):
            fechas_ct.add(s - pd.Timedelta(days=k))
    ctrl_C = [(s, e) for s, e in ctrl_A if s in
              {d.date() if hasattr(d, "date") else d for d in fechas_ct}]

    r_ev = [retorno(mapas, s, e) for s, e in ev]
    r_A = [retorno(mapas, s, e) for s, e in ctrl_A]
    r_B = [retorno(mapas, s, e) for s, e in ctrl_B]
    r_C = [retorno(mapas, s, e) for s, e in ctrl_C]

    print()
    print("=" * 84)
    print("VENTANA VIVA  ·  entrada %s del dia anterior -> salida %s"
          % ("15:57", "09:30"))
    print("=" * 84)
    print("  %-34s%6s%10s%9s%9s" % ("serie", "n", "media bp", "sd", "se"))
    print("  " + "-" * 70)
    for etq, r in [("noches pre-FOMC", r_ev),
                   ("control A · todas las noches", r_A),
                   ("control B · solo miercoles", r_B),
                   ("control C · -7 y -14 dias", r_C)]:
        s = resumen(r)
        print("  %-34s%6d%10.2f%9.1f%9.2f"
              % (etq, s["n"], s["media"], s["sd"], s["se"]))

    x = np.array([v for v in r_ev if v is not None])
    print()
    print("  contraste contra cada control (Welch):")
    for etq, r in [("A todas", r_A), ("B miercoles", r_B), ("C -7/-14", r_C)]:
        y = np.array([v for v in r if v is not None])
        t, p = stats.ttest_ind(x, y, equal_var=False)
        print("     vs %-14s dif %+7.2f bp   t = %+5.2f   p = %.3f"
              % (etq, x.mean() - y.mean(), t, p))

    # ---- por tramos, contra los dos controles que aguantan
    print()
    print("=" * 84)
    print("POR TRAMOS  ·  el tramo que decide es el ULTIMO, que es el que se opera")
    print("=" * 84)
    for nom_c, ctrl in [("B · todas las noches de miercoles", ctrl_B),
                        ("C · mismo dia de la semana a -7/-14", ctrl_C)]:
        print("\n  control %s" % nom_c)
        print("  %-14s%5s%10s%10s%9s%8s%8s" %
              ("tramo", "n", "FOMC bp", "ctrl bp", "dif", "t", "p"))
        print("  " + "-" * 66)
        for etq, a, b in [("2011-2015", 2011, 2015), ("2016-2020", 2016, 2020),
                          ("2021-2026", 2021, 2026), ("TODO", 2011, 2026),
                          ("2016-2026", 2016, 2026)]:
            xa = np.array([retorno(mapas, s, e) for s, e in ev
                           if a <= s.year <= b], dtype=float)
            ya = np.array([retorno(mapas, s, e) for s, e in ctrl
                           if a <= s.year <= b], dtype=float)
            xa, ya = xa[~np.isnan(xa)], ya[~np.isnan(ya)]
            if len(xa) < 5 or len(ya) < 5:
                continue
            t, p = stats.ttest_ind(xa, ya, equal_var=False)
            print("  %-14s%5d%10.2f%10.2f%9.2f%8.2f%8.3f"
                  % (etq, len(xa), xa.mean(), ya.mean(),
                     xa.mean() - ya.mean(), t, p))

    # ---- PLACEBO: la maquinaria aplicada a noches que no son evento.
    # Fase 7.5: "pon siempre un control negativo". Si el montaje encuentra
    # +19 bp donde no hay anuncio, no esta midiendo el FOMC.
    print()
    print("=" * 84)
    print("PLACEBO  ·  el mismo montaje sobre noches SIN anuncio")
    print("=" * 84)
    print("  %-22s%6s%10s%10s%9s%8s%8s"
          % ("evento falso", "n", "medio", "ctrl", "dif", "t", "p"))
    print("  " + "-" * 74)
    for desp in (7, 14, 21, 28):
        falsas = set()
        for s, _ in ev:
            falsas.add(s - pd.Timedelta(days=desp))
        falsas = {d.date() if hasattr(d, "date") else d for d in falsas}
        pl = [(s, e) for s, e in todas if s in falsas and (s, e) not in set_ev]
        if len(pl) < 20:
            continue
        # control del placebo: mismo dia de la semana, otras 7/14 semanas
        ref = set()
        for s, _ in pl:
            for k in (7, 14):
                ref.add(s - pd.Timedelta(days=k))
        ref = {d.date() if hasattr(d, "date") else d for d in ref}
        pc = [(s, e) for s, e in todas
              if s in ref and (s, e) not in set_ev and s not in falsas]
        xp = np.array([retorno(mapas, s, e) for s, e in pl], dtype=float)
        yp = np.array([retorno(mapas, s, e) for s, e in pc], dtype=float)
        xp, yp = xp[~np.isnan(xp)], yp[~np.isnan(yp)]
        if len(xp) < 20 or len(yp) < 20:
            continue
        t, p = stats.ttest_ind(xp, yp, equal_var=False)
        print("  %-22s%6d%10.2f%10.2f%9.2f%8.2f%8.3f"
              % ("FOMC menos %d dias" % desp, len(xp), xp.mean(), yp.mean(),
                 xp.mean() - yp.mean(), t, p))
    print()
    print("  Si estas filas dan diferencias del tamano del efecto real, el")
    print("  montaje fabrica ventaja y no hay nada que discutir.")

    # ---- rejilla: se publican las medias y se cuentan cambios de signo
    print()
    print("=" * 84)
    print("REJILLA DE ESPECIFICACIONES  ·  medias en bp (Fase 6: contar signos)")
    print("=" * 84)
    print("  %-10s" % "entrada" + "".join("%10s" % n for _, n in SALIDAS))
    print("  " + "-" * 52)
    medias, ts = [], []
    for me, ne in ENTRADAS:
        fila = []
        for ms, ns in SALIDAS:
            v = np.array([retorno(mapas, s, e, me, ms) for s, e in ev],
                         dtype=float)
            v = v[~np.isnan(v)]
            c = np.array([retorno(mapas, s, e, me, ms) for s, e in ctrl_C],
                         dtype=float)
            c = c[~np.isnan(c)]
            d = v.mean() - c.mean()
            t, _ = stats.ttest_ind(v, c, equal_var=False)
            fila.append(d)
            medias.append(d)
            ts.append(t)
        print("  %-10s" % ne + "".join("%10.2f" % z for z in fila))
    medias, ts = np.array(medias), np.array(ts)
    print()
    print("  celdas                 : %d" % len(medias))
    print("  con la media NEGATIVA  : %d  (%.0f%%)"
          % (int((medias < 0).sum()), 100.0 * (medias < 0).mean()))
    print("  rango de las medias    : %+.1f a %+.1f bp"
          % (medias.min(), medias.max()))
    print("  celdas con t > 2       : %d de %d" % (int((ts > 2).sum()), len(ts)))
    print()
    print("  Referencia de la Fase 6: la rejilla que se declaro solida tenia")
    print("  0%% de celdas negativas y medias de +18,9 a +32,2 bp.")

    # ---------------------------------------------------------------- fricción
    # Parametros de la configuracion viva (ESTADO-CUENTA) y del bróker.
    CUENTA, RIESGO, STOP_BP = 25000.0, 0.0110, 80.0
    SPREAD_BP, SWAP_ANUAL, UNID_ANIO = 1.37, 0.064, 364.0
    nocional = CUENTA * RIESGO / (STOP_BP / 1e4)
    bp_unidad = SWAP_ANUAL / UNID_ANIO * 1e4
    ida_vuelta = 2 * SPREAD_BP

    print()
    print("=" * 84)
    print("LA VENTAJA, NETA DE FRICCION  ·  y la regla de dimensionado 12.1")
    print("=" * 84)
    print("  nocional implicito = %.0f$ x %.2f%% / %.0f bp = %.0f $"
          % (CUENTA, RIESGO * 100, STOP_BP, nocional))
    print("  coste ida y vuelta = 2 x %.2f bp = %.2f bp" % (SPREAD_BP, ida_vuelta))
    print("  una unidad de swap = %.2f%% / %.0f = %.2f bp del nocional"
          % (SWAP_ANUAL * 100, UNID_ANIO, bp_unidad))
    print()
    print("  El anuncio es en miercoles y la entrada cae el martes por la tarde.")
    print("  El rollover es a las 00:00 del servidor = 18:00 NY, asi que la")
    print("  posicion SIEMPRE cruza uno. Cuantas unidades cobra ese cruce")
    print("  depende de a que rollover asigna el broker el triple, y eso NO")
    print("  esta verificado: se resuelve con la cuenta abierta, midiendo")
    print("  swap = (equity - saldo) - suma(Profit) tras un rollover (Fase 15).")
    print()
    print("  %-30s%9s%9s%9s%9s" % ("escenario", "bruta", "friccion", "neta", "f=0?"))
    print("  " + "-" * 68)
    for nom_c, ctrl in [("vs B miercoles", ctrl_B), ("vs C -7/-14", ctrl_C)]:
        y = np.array([v for v in
                      [retorno(mapas, s, e) for s, e in ctrl] if v is not None])
        bruta = x.mean() - y.mean()
        se_d = np.sqrt(x.std(ddof=1) ** 2 / len(x) + y.std(ddof=1) ** 2 / len(y))
        for unid in (1, 3):
            fr = ida_vuelta + unid * bp_unidad
            neta = bruta - fr
            defendible = neta - 2 * se_d
            print("  %-30s%9.2f%9.2f%9.2f%9s"
                  % ("%s, %d unid. swap" % (nom_c, unid), bruta, fr, neta,
                     "SI  f=0" if defendible <= 0 else "no  %+.2f" % defendible))
    print()
    print("  La columna f=0 aplica la regla de la Fase 12.1: el tamano")
    print("  defendible es f*(ventaja - 2 x error tipico). Si sale <= 0, la")
    print("  medicion no soporta ninguna posicion, con independencia del signo.")
    print("  Error tipico de la diferencia: %.2f bp (vs B) — el efecto tendria"
          % np.sqrt(x.std(ddof=1) ** 2 / len(x)
                    + np.array([v for v in [retorno(mapas, s, e)
                                            for s, e in ctrl_B]
                                if v is not None]).std(ddof=1) ** 2 / len(ctrl_B)))
    print("  que ser el doble de eso para justificar tamano.")


if __name__ == "__main__":
    main()
