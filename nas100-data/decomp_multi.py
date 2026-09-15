#!/usr/bin/env python3
"""
REPLICACION CRUZADA de la descomposicion intradia / nocturno.

Referencia medida en NASDAQ sobre 3.682 sesiones:
    intradia  Sharpe 0.51      nocturno  Sharpe 0.71
    correlacion entre los dos: -0.007   (ortogonales)

La pregunta: ¿es un efecto real o una peculiaridad del NASDAQ?

Disciplina aplicada:
  - UNA hipotesis, muchos instrumentos. La correccion multiple va sobre la
    hipotesis, no sobre los instrumentos.
  - Los cuatro indices de EE.UU. NO son cuatro pruebas independientes
    (correlacion ~0,9). Se agrupan en bloques y se cuenta por bloque.
  - ORO como CONTROL NEGATIVO: no tiene sesion de contado, asi que el corte
    es arbitrario. Si el efecto aparece igual ahi, huele a artefacto.
  - Las horas de sesion se VERIFICAN sobre los datos, no se asumen.
"""
import os
import glob
import numpy as np
import pandas as pd

DIR_MULTI = "raw-multi"
DIR_NAS = "raw"

# instrumento -> (zona horaria, apertura, cierre, etiqueta, bloque)
CFG = {
    "usatechidxusd":  ("America/New_York", "09:30", "16:00", "NASDAQ 100",   "EEUU"),
    "usa500idxusd":   ("America/New_York", "09:30", "16:00", "S&P 500",      "EEUU"),
    "usa30idxusd":    ("America/New_York", "09:30", "16:00", "Dow 30",       "EEUU"),
    "ussc2000idxusd": ("America/New_York", "09:30", "16:00", "Russell 2000", "EEUU"),
    "deuidxeur":      ("Europe/Berlin",    "09:00", "17:30", "DAX",          "EUROPA"),
    "gbridxgbp":      ("Europe/London",    "08:00", "16:30", "FTSE 100",     "EUROPA"),
    "jpnidxjpy":      ("Asia/Tokyo",       "09:00", "15:00", "Nikkei 225",   "ASIA"),
    "xauusd":         ("America/New_York", "09:30", "16:00", "ORO (control)", "CONTROL"),
}


def cargar(clave):
    if clave == "usatechidxusd":
        fs = sorted(glob.glob(os.path.join(DIR_NAS, "usatechidxusd-m1-*.csv")))
        if not fs:
            return None
        df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    else:
        p = os.path.join(DIR_MULTI, "%s-m15.csv" % clave)
        if not os.path.exists(p):
            return None
        df = pd.read_csv(p)
    col = df.columns[0]
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col])
    df["ts"] = pd.to_datetime(df[col], unit="ms", utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def verificar_horas(df, tz, etiqueta):
    loc = df["ts"].dt.tz_convert(tz)
    h = loc.dt.hour
    vc = h.value_counts().sort_index()
    activas = vc[vc > 0.15 * vc.max()]
    return int(activas.index.min()), int(activas.index.max()), vc


def descomponer(df, tz, ini, fin):
    loc = df["ts"].dt.tz_convert(tz)
    d = pd.DataFrame({
        "dia": loc.dt.date,
        "hm": loc.dt.strftime("%H:%M"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
    }).dropna()
    d = d[(d["hm"] >= ini) & (d["hm"] <= fin)]
    g = d.groupby("dia")["close"]
    ses = pd.DataFrame({"apertura": g.first(), "cierre": g.last(),
                        "n": g.size()})
    ses = ses[ses["n"] >= 5]
    ses["cierre_prev"] = ses["cierre"].shift(1)
    ses = ses.dropna()
    ses["r_noct"] = ses["apertura"] / ses["cierre_prev"] - 1.0
    ses["r_intra"] = ses["cierre"] / ses["apertura"] - 1.0
    # se recortan saltos absurdos de feed (>15% en un tramo)
    ses = ses[(ses["r_noct"].abs() < 0.15) & (ses["r_intra"].abs() < 0.15)]
    return ses


def sharpe(r):
    if len(r) < 100 or r.std() == 0:
        return np.nan, np.nan
    s = r.mean() / r.std() * np.sqrt(252)
    se = np.sqrt((1 + s * s / 2) / (len(r) / 252.0))
    return s, se


print("=" * 84)
print("VERIFICACION DE HORAS DE SESION (sobre los datos, no asumidas)")
print("=" * 84)
print(f"{'instrumento':<16}{'zona':<20}{'horas con datos':>18}"
      f"{'ventana usada':>18}")
print("-" * 84)
datos = {}
for clave, (tz, ini, fin, etq, blq) in CFG.items():
    df = cargar(clave)
    if df is None:
        print(f"{etq:<16}{'[sin datos aun]':<20}")
        continue
    lo, hi, _ = verificar_horas(df, tz, etq)
    datos[clave] = df
    print(f"{etq:<16}{tz:<20}{('%02dh - %02dh' % (lo, hi)):>18}"
          f"{(ini + ' - ' + fin):>18}")

print()
print("=" * 84)
print("DESCOMPOSICION INTRADIA / NOCTURNO")
print("=" * 84)
print(f"{'instrumento':<16}{'bloque':<9}{'sesiones':>9}"
      f"{'Sh NOCT':>16}{'Sh INTRA':>16}{'rho':>9}")
print("-" * 84)

res = {}
for clave, (tz, ini, fin, etq, blq) in CFG.items():
    if clave not in datos:
        continue
    ses = descomponer(datos[clave], tz, ini, fin)
    if len(ses) < 200:
        print(f"{etq:<16}{blq:<9}{len(ses):>9}   [muestra insuficiente]")
        continue
    sn, en = sharpe(ses["r_noct"])
    si, ei = sharpe(ses["r_intra"])
    rho = ses["r_noct"].corr(ses["r_intra"])
    res[clave] = dict(etq=etq, blq=blq, n=len(ses), sn=sn, en=en,
                      si=si, ei=ei, rho=rho)
    print(f"{etq:<16}{blq:<9}{len(ses):>9}"
          f"{('%+.2f ± %.2f' % (sn, en)):>16}"
          f"{('%+.2f ± %.2f' % (si, ei)):>16}{rho:>9.3f}")

# ------------------------------------------------------ lectura por bloques
print()
print("=" * 84)
print("RECUENTO POR BLOQUE INDEPENDIENTE")
print("(los 4 de EE.UU. cuentan como UNO: estan correlacionados ~0,9)")
print("=" * 84)
bloques = {}
for r in res.values():
    bloques.setdefault(r["blq"], []).append(r)

print(f"{'bloque':<10}{'n instr':>8}{'Sh NOCT medio':>16}"
      f"{'Sh INTRA medio':>17}{'rho medio':>11}{'noct > 0':>10}")
print("-" * 84)
for blq in ("EEUU", "EUROPA", "ASIA", "CONTROL"):
    if blq not in bloques:
        continue
    L = bloques[blq]
    mn = np.nanmean([x["sn"] for x in L])
    mi = np.nanmean([x["si"] for x in L])
    mr = np.nanmean([x["rho"] for x in L])
    pos = sum(1 for x in L if x["sn"] > 0)
    print(f"{blq:<10}{len(L):>8}{mn:>16.2f}{mi:>17.2f}{mr:>11.3f}"
          f"{('%d/%d' % (pos, len(L))):>10}")

print()
print("=" * 84)
print("CONTRASTE CON LA REFERENCIA DEL NASDAQ")
print("=" * 84)
print("  medido antes en NASDAQ (M1, 3.682 sesiones):")
print("     nocturno Sharpe 0.71 · intradia 0.51 · rho -0.007")
print()
reales = [x for x in res.values() if x["blq"] != "CONTROL"]
if reales:
    n_noct_pos = sum(1 for x in reales if x["sn"] > 0)
    n_domina = sum(1 for x in reales if x["sn"] > x["si"])
    print("  instrumentos (sin contar el control): %d" % len(reales))
    print("  con Sharpe nocturno > 0            : %d" % n_noct_pos)
    print("  con nocturno > intradia            : %d" % n_domina)
    rhos = [x["rho"] for x in reales if not np.isnan(x["rho"])]
    print("  rho intradia-nocturno: media %+.3f  ·  max |rho| %.3f"
          % (np.mean(rhos), np.max(np.abs(rhos))))
ctrl = [x for x in res.values() if x["blq"] == "CONTROL"]
if ctrl:
    c = ctrl[0]
    print()
    print("  CONTROL NEGATIVO (oro, corte de sesion arbitrario):")
    print("     nocturno %+.2f ± %.2f · intradia %+.2f ± %.2f · rho %+.3f"
          % (c["sn"], c["en"], c["si"], c["ei"], c["rho"]))
    print("     -> si aqui tambien sale un nocturno fuerte, el efecto no es")
    print("        una prima de riesgo de renta variable sino un artefacto")
    print("        del corte horario o del feed.")
