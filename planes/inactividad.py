#!/usr/bin/env python3
"""
¿PUEDE EL SISTEMA QUEDARSE 35 DIAS SIN CERRAR UNA OPERACION?

Regla de Upcomers para cuentas CFD: 35 dias naturales consecutivos sin
actividad y la cuenta EXPIRA y se marca como fallida. Y el detalle que
importa: el contador se reinicia cuando se CIERRA una operacion, no cuando se
abre. Mantener siete posiciones abiertas un mes NO es actividad.

Nuestro sistema produce cierres en dos sitios:
  · la #1 pre-FOMC cierra su posicion en CADA evento (8 al año)
  · la #2 trend cierra algo en un rebalanceo SOLO si una señal cambia de signo
    o si el tamaño objetivo se desvia mas del 20% del actual

Si un mes el umbral del 20% mantiene las siete posiciones, ese rebalanceo NO
genera ningun cierre. Y los huecos del calendario del FOMC son largos.

Se miden las dos cosas y se combinan.
"""
import re
import datetime as dt
import numpy as np
import pandas as pd

# ------------------------------------------------ 1. huecos del FOMC
FECHAS = sorted(set(re.findall(
    r"\b(20\d{6})\b",
    open("../mql5/fechas_fomc_completas.txt", encoding="utf-8").read())))
DS = [dt.date(int(f[:4]), int(f[4:6]), int(f[6:])) for f in FECHAS]
huecos = [(DS[i+1] - DS[i]).days for i in range(len(DS)-1)]

E = "=" * 84
print(E)
print("1. HUECOS ENTRE ANUNCIOS DEL FOMC  (cada anuncio produce un cierre)")
print(E)
h = np.array(huecos)
print(f"  anuncios en la tabla : {len(DS)}   ({DS[0]} -> {DS[-1]})")
print(f"  hueco medio          : {h.mean():.0f} dias")
print(f"  hueco mediano        : {np.median(h):.0f} dias")
print(f"  hueco MAXIMO         : {h.max()} dias")
print(f"  huecos > 35 dias     : {(h > 35).sum()} de {len(h)} ({(h>35).mean():.0%})")
print()
print("  Los proximos huecos, con las fechas que lleva el EA embebidas:")
hoy = dt.date(2026, 9, 4)
prox = [d for d in DS if d >= hoy][:8]
for i in range(len(prox)-1):
    g = (prox[i+1] - prox[i]).days
    al = "  <- EXCEDE 35" if g > 35 else ""
    print(f"     {prox[i]}  ->  {prox[i+1]}   {g:>3} dias{al}")

# ------------------------------------------------ 2. cierres del trend
print()
print(E)
print("2. ¿CUANTOS REBALANCEOS DEL TREND CIERRAN ALGO?")
print(E)

CESTA = {
    "SPCUSD.c": "../trend/datos/SPY.csv",
    "NACUSD.c": "../trend/datos/QQQ.csv",
    "XAUUSD":   "../trend/datos/GLD.csv",
    "XAGUSD":   "../trend/datos/SLV.csv",
    "EURUSD":   "../trend/datos/EURUSDX.csv",
    "USDJPY":   "../trend/datos/USDJPYX.csv",
    "GBPUSD":   "../trend/datos/GBPUSDX.csv",
    "AUDUSD":   "../trend/datos/AUDUSDX.csv",
}
VOL_OBJ, MIRADA, TOPE, DIVISOR, DIAS_VOL = 0.0723, 12, 5.0, 8, 150
UMBRAL = 0.20                 # InpUmbralCambio

pos_por_mes = {}
for nom, p in CESTA.items():
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    s = s[s > 0]
    r_d = s.pct_change().dropna()
    vol = (r_d.rolling(DIAS_VOL).std(ddof=1) * np.sqrt(252)).resample("ME").last()
    m = s.resample("ME").last()
    ser = {}
    for i in range(MIRADA + 1, len(m)):
        pas = m.iloc[i-1] / m.iloc[i-1-MIRADA] - 1.0
        v = vol.iloc[i-1]
        if pd.isna(pas) or pd.isna(v) or v <= 0:
            continue
        ser[m.index[i]] = float(np.clip(np.sign(pas) * (VOL_OBJ / v),
                                        -TOPE, TOPE)) / DIVISOR
    pos_por_mes[nom] = pd.Series(ser).sort_index()

P = pd.DataFrame(pos_por_mes).dropna(how="all")
P = P[P.notna().sum(axis=1) >= 6]

meses, con_cierre, detalle = 0, 0, []
actual = {k: 0.0 for k in CESTA}
for fecha, fila in P.iterrows():
    meses += 1
    cierres = 0
    for nom in CESTA:
        obj = fila.get(nom, np.nan)
        if pd.isna(obj):
            continue
        act = actual[nom]
        if act == 0.0:
            actual[nom] = obj          # apertura, no cierre
            continue
        mismo_lado = obj * act > 0
        cambio = abs(obj - act)
        if (not mismo_lado) or cambio > abs(obj) * UMBRAL:
            cierres += 1               # cierra y reabre
            actual[nom] = obj
    detalle.append((fecha, cierres))
    if cierres > 0:
        con_cierre += 1

cs = np.array([c for _, c in detalle])
print(f"  rebalanceos simulados        : {meses}")
print(f"  con al menos UN cierre       : {con_cierre} ({con_cierre/meses:.1%})")
print(f"  SIN ningun cierre            : {meses-con_cierre} "
      f"({1-con_cierre/meses:.1%})")
print(f"  cierres por rebalanceo       : media {cs.mean():.2f}  ·  "
      f"mediana {np.median(cs):.0f}  ·  minimo {cs.min()}")
print()
print(f"  {'cierres en el mes':>18}{'nº de meses':>14}{'%':>8}")
print("  " + "-" * 40)
for k in range(0, min(cs.max(), 8) + 1):
    n = (cs == k).sum()
    if n:
        print(f"  {k:>18}{n:>14}{n/meses:>7.1%}")

# racha maxima de meses seguidos sin cierre
racha, peor = 0, 0
for _, c in detalle:
    racha = racha + 1 if c == 0 else 0
    peor = max(peor, racha)
print(f"\n  racha maxima de meses consecutivos SIN cierre: {peor}")

# ------------------------------------------------ 3. combinado
print()
print(E)
print("3. EL RIESGO COMBINADO")
print(E)
p_sin = 1 - con_cierre / meses
print(f"  P(un rebalanceo no cierra nada)          : {p_sin:.1%}")
print()
print("  Escenario que rompe la cuenta: un hueco del FOMC de mas de 35 dias")
print("  con un rebalanceo en medio que no cierra nada.")
print()
n_grandes = (h > 35).sum()
print(f"  huecos del FOMC > 35 dias en el historico: {n_grandes} de {len(h)}")
print(f"  P(rebalanceo sin cierre) x P(hueco largo) = "
      f"{p_sin:.1%} x {(h>35).mean():.0%} = {p_sin*(h>35).mean():.2%} por hueco")
print()
print(f"  con 8 huecos al año: {p_sin*(h>35).mean()*8:.1%} de probabilidad anual")
print("  de que la cuenta expire por inactividad")
print()
print("  Y ojo con el arranque: el contador empieza EN LA COMPRA, no en la")
print("  primera operacion. Cuenta comprada el 2 de septiembre ->")
print(f"  primer vencimiento el {dt.date(2026,9,2)+dt.timedelta(days=35)}.")
