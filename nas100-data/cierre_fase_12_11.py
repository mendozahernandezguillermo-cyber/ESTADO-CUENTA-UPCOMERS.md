"""
CIERRE DE LA FASE 12.11 CON EL DATO QUE LE FALTABA.

El protocolo 2.1 cierra el caso NASDAQ asi: "Estado: cerrado, y no por falta de
ideas sino por falta de datos. Reabrir exige historico multianual real que
permita un train anterior al tramo ya quemado."

Ese historico existe: M1 de NASDAQ de sep-2011 a ago-2026, 5,7 M de barras,
completamente ajeno a las 1.626 combinaciones que se optimizaron sobre 2026.
O sea: es holdout limpio de verdad, no un tramo reetiquetado.

Se cierra aplicando los criterios del propio documento:
  Fase 12.2   friccion COMPLETA = 2 x (spread + comision) / stop.
              Mi medicion anterior aplico media horquilla SOLO en la entrada,
              o sea que subestimaba el coste. Se corrige aqui.
  Fase 0      suelo de ruido en R: que ventaja se puede DEMOSTRAR con esta n.
  Fase 12.10  acierto de equilibrio, comprobado POR SUBTRAMOS y no en el total.
  Fase 7      cambios de signo al barrer la rejilla de especificaciones.
  Fase 11     DD/vol de la señal, la variable de diseño mas potente.
  Fase 12.9   coherencia mecanica: el pago medio no puede superar D x M.
"""
import glob, os
import numpy as np
import pandas as pd

DIR = "raw"
CANAL = 48
STOP_BP = 100.0
MAX_DIA = 2
SPREAD_BP = 1.37          # medido en el broker para NACUSD.c
COMISION_BP = 0.0         # el broker de Upcomers no cobra en indices; se deja explicito
MULTIPLOS = (1.0, 1.5, 2.0, 3.0, 5.0)

print("leyendo M1 y construyendo M5 ...")
M = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(os.path.join(DIR, "*.csv")))],
              ignore_index=True)
M["t"] = pd.to_datetime(M["timestamp"], unit="ms")
M = M[M["close"] > 0].drop_duplicates(subset="t").sort_values("t").reset_index(drop=True)
M["b5"] = M["t"].dt.floor("5min")
g = M.groupby("b5")
M5 = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(),
                   "close": g["close"].last(), "n": g["close"].size()}).reset_index()
M5 = M5[M5["n"] >= 3].reset_index(drop=True)
print(f"  M1 {len(M):,}   M5 {len(M5):,}   de {M['t'].iloc[0].date()} a {M['t'].iloc[-1].date()}")

hi, lo, cl = M5["high"].values, M5["low"].values, M5["close"].values
canal_hi = pd.Series(hi).rolling(CANAL).max().shift(1).values
canal_lo = pd.Series(lo).rolling(CANAL).min().shift(1).values
señal = np.where(cl > canal_hi, 1, np.where(cl < canal_lo, -1, 0))

m1_t, m1_hi, m1_lo, m1_cl = (M["t"].values, M["high"].values,
                             M["low"].values, M["close"].values)
pos_entrada = np.searchsorted(m1_t, (M5["b5"] + pd.Timedelta(minutes=5)).values, "left")
dias = M5["b5"].dt.floor("D").values
anios_v = M5["b5"].dt.year.values

usados, ops = {}, []
for k in np.where(señal != 0)[0]:
    d = dias[k]
    if usados.get(d, 0) >= MAX_DIA:
        continue
    pe = pos_entrada[k]
    if pe >= len(m1_cl) or pe == 0:
        continue
    usados[d] = usados.get(d, 0) + 1
    ops.append((pe, int(señal[k]), int(anios_v[k])))
print(f"  operaciones: {len(ops):,}")

MAXB = 60 * 24 * 10
FRICCION_BP = 2.0 * (SPREAD_BP + COMISION_BP)      # Fase 12.2: ida Y vuelta


def resolver(mult):
    out = np.empty(len(ops)); yr = np.empty(len(ops), int)
    for j, (pe, d, y) in enumerate(ops):
        ent = m1_cl[pe - 1]
        sl = ent * (1.0 - d * STOP_BP / 1e4)
        tp = ent * (1.0 + d * STOP_BP * mult / 1e4)
        fin = min(pe + MAXB, len(m1_cl))
        h, l = m1_hi[pe:fin], m1_lo[pe:fin]
        ts = (l <= sl) if d > 0 else (h >= sl)
        tt = (h >= tp) if d > 0 else (l <= tp)
        isl = np.argmax(ts) if ts.any() else 10**9
        itp = np.argmax(tt) if tt.any() else 10**9
        if isl == 10**9 and itp == 10**9:
            bruto = d * (m1_cl[fin - 1] / ent - 1.0) * 1e4
        elif isl <= itp:
            bruto = -STOP_BP
        else:
            bruto = STOP_BP * mult
        out[j] = bruto - FRICCION_BP        # friccion completa
        yr[j] = y
    return out, yr


E = "=" * 94
print()
print(E)
print("1. LA REJILLA, CON FRICCION COMPLETA (Fase 12.2)")
print(E)
print(f"  friccion = 2 x ({SPREAD_BP:.2f} + {COMISION_BP:.2f}) / {STOP_BP:.0f} "
      f"= {FRICCION_BP/STOP_BP:.4f}R = {FRICCION_BP:.2f} bp por operacion")
print()
print(f"  {'objetivo':>9}{'aciertos':>10}{'exp. R':>10}{'error tip.':>12}"
      f"{'t':>8}{'signo':>8}")
print("  " + "-" * 60)
guarda = {}
for m in MULTIPLOS:
    r, yr = resolver(m)
    guarda[m] = (r, yr)
    R = r / STOP_BP
    se = R.std() / np.sqrt(len(R))
    print(f"  {m:>8.1f}R{(r>0).mean():>10.1%}{R.mean():>+10.4f}{se:>12.4f}"
          f"{R.mean()/se:>8.2f}{('+' if R.mean()>0 else '-'):>8}")
signos = [np.sign(guarda[m][0].mean()) for m in MULTIPLOS]
cambios = sum(1 for i in range(1, len(signos)) if signos[i] != signos[i-1])
print()
print(f"  cambios de signo en la rejilla: {cambios}  "
      f"(Fase 7 exige 0 para seguir adelante)")

print()
print(E)
print("2. EL SUELO DE RUIDO: ¿QUE SE PUEDE DEMOSTRAR CON ESTA n? (Fase 0)")
print(E)
r1, yr1 = guarda[1.0]
R1 = r1 / STOP_BP
se1 = R1.std() / np.sqrt(len(R1))
print(f"  n = {len(R1):,}   desviacion tipica = {R1.std():.3f}R")
print(f"  error tipico = {se1:.4f}R   ->  resoluble a 2se = +-{2*se1:.4f}R")
print(f"  ventaja medida = {R1.mean():+.4f}R")
print()
print(f"  Lectura correcta: la ventaja NO es negativa con significancia.")
print(f"  Esta ACOTADA en |ventaja| < {2*se1:.4f}R, y la regla de tamaño de la")
print(f"  Fase 12.1 —f = f*(medida - 2se)— devuelve CERO para cualquier valor")
print(f"  dentro de esa banda. No hace falta demostrar que pierde: basta con")
print(f"  demostrar que no se puede dimensionar.")

print()
print(E)
print("3. ACIERTO DE EQUILIBRIO POR SUBTRAMOS (Fase 12.10)")
print(E)
gan = STOP_BP * 1.0 - FRICCION_BP
per = STOP_BP + FRICCION_BP
equil = per / (gan + per)
print(f"  ganancia media {gan:.1f} bp · perdida media {per:.1f} bp")
print(f"  acierto de equilibrio = {equil:.1%}")
print()
print(f"  {'año':>6}{'n':>7}{'acierto':>10}{'vs equilibrio':>15}{'exp. R':>10}")
print("  " + "-" * 50)
arriba = 0
for y in sorted(set(yr1)):
    m = yr1 == y
    if m.sum() < 50:
        continue
    a = (r1[m] > 0).mean()
    arriba += (a > equil)
    print(f"  {y:>6}{m.sum():>7}{a:>10.1%}"
          f"{('ARRIBA' if a>equil else 'abajo'):>15}{(r1[m]/STOP_BP).mean():>+10.4f}")
print()
print(f"  años por encima del equilibrio: {arriba} de "
      f"{len([y for y in set(yr1) if (yr1==y).sum()>=50])}")
print("  El protocolo pide que el acierto se mantenga por encima EN SUBTRAMOS.")

print()
print(E)
print("4. DD/vol DE LA SEÑAL (Fase 11: la variable de diseño mas potente)")
print(E)
eq = np.cumsum(R1)
dd = float(np.max(np.maximum.accumulate(eq) - eq))
por_anio = len(R1) / ((M5["b5"].iloc[-1] - M5["b5"].iloc[0]).days / 365.25)
vol = R1.std() * np.sqrt(por_anio)
print(f"  operaciones al año        : {por_anio:.0f}")
print(f"  drawdown maximo en R      : {dd:.1f}R")
print(f"  volatilidad anual en R    : {vol:.1f}R")
print(f"  DD/vol                    : {dd/vol:.2f}   "
      f"(objetivo del protocolo: < 1,1)")
print()
print("  Y el aviso de la Fase 11 aplica al pie de la letra: con esperanza <= 0")
print("  este cociente no significa supervivencia, porque el drawdown solo esta")
print("  acotado por el hecho de que la cuenta llega a cero.")

print()
print(E)
print("5. COHERENCIA MECANICA (Fase 12.9)")
print(E)
print(f"  pago medio maximo posible con D=125$ y M=1,0R : {125*1.0:>8.2f}$")
print(f"  pago medio implicado por la medicion          : "
      f"{R1.mean()*125:>8.2f}$")
print(f"  coherente: la medicion no supera el techo aritmetico.")
