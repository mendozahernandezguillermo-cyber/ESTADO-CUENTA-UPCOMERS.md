#!/usr/bin/env python3
"""
EL BROKER SOLO TIENE 8 MESES. ¿SE PUEDE OPERAR ESTO IGUAL?

Situacion medida en el terminal: los ocho simbolos tienen historial desde el
12-16 de enero de 2026, sincronizado. 163-179 barras D1 y 9 barras MN1.
La señal necesita 14 MN1 y la volatilidad 254 D1.

La estrategia necesita exactamente DOS numeros por mercado y por mes:
    1. el SIGNO del retorno de 12 meses   -> imposible con 8 meses de datos
    2. la VOLATILIDAD anualizada          -> ¿basta con 163 dias?

Si la respuesta a (2) es que si, entonces solo hay que traer de fuera el
signo, que es un +1 o un -1 por mercado. Eso es un fichero de ocho lineas y
cambia pocas veces al año.

Este script mide las tres cosas que deciden si el plan es sensato:
  A. cuanto se desvia una vol de 163 dias de la de 252
  B. cuanto cuesta esa desviacion en el dimensionado
  C. con que frecuencia cambia el signo, o sea cuanto puede envejecer el
     fichero antes de que importe
"""
import numpy as np
import pandas as pd

CESTA = {
    "SPCUSD.c": "datos/SPY.csv",
    "NACUSD.c": "datos/QQQ.csv",
    "XAUUSD":   "datos/GLD.csv",
    "XAGUSD":   "datos/SLV.csv",
    "EURUSD":   "datos/EURUSDX.csv",
    "USDJPY":   "datos/USDJPYX.csv",
    "GBPUSD":   "datos/GBPUSDX.csv",
    "AUDUSD":   "datos/AUDUSDX.csv",
}
VOL_OBJ = 7.23 / 100.0
TOPE = 5.0
DIVISOR = 8
CORTO = 163          # lo que de verdad hay
LARGO = 252          # lo que pide la especificacion

series = {}
for nom, p in CESTA.items():
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    series[nom] = s[s > 0]

E = "=" * 88
print(E)
print("A) ¿SIRVE UNA VOLATILIDAD DE 163 DIAS EN VEZ DE 252?")
print(E)
print(f"  {'mercado':<11}{'corr(163,252)':>15}{'sesgo medio':>14}"
      f"{'desv. media abs':>17}{'p95 del error':>15}")
print("  " + "-" * 72)
errores_todos = []
for nom, s in series.items():
    r = s.pct_change().dropna()
    v_l = r.rolling(LARGO).std(ddof=1) * np.sqrt(252)
    v_c = r.rolling(CORTO).std(ddof=1) * np.sqrt(252)
    D = pd.DataFrame({"l": v_l, "c": v_c}).dropna()
    err = (D["c"] / D["l"] - 1.0)
    errores_todos.append(err)
    print(f"  {nom:<11}{D['c'].corr(D['l']):>15.3f}{err.mean():>+14.1%}"
          f"{err.abs().mean():>17.1%}{err.abs().quantile(0.95):>15.1%}")

todos = pd.concat(errores_todos)
print("  " + "-" * 72)
print(f"  {'CONJUNTO':<11}{'':>15}{todos.mean():>+14.1%}"
      f"{todos.abs().mean():>17.1%}{todos.abs().quantile(0.95):>15.1%}")

print()
print(E)
print("B) ¿CUANTO CUESTA ESA DESVIACION EN EL DIMENSIONADO?")
print(E)
print("  La exposicion es inversamente proporcional a la vol, asi que un error")
print("  del x% en la vol es un error del x% (al reves) en el tamaño.")
print()
# reconstruir la serie de la cartera con vol corta y con vol larga
def serie_trend(dias_vol):
    diarias = {}
    for nom, s in series.items():
        r_d = s.pct_change().dropna()
        vol = r_d.rolling(dias_vol).std(ddof=1) * np.sqrt(252)
        m = s.resample("ME").last()
        vol_m = vol.resample("ME").last()
        pos = {}
        for i in range(13, len(m)):
            pas = m.iloc[i - 1] / m.iloc[i - 13] - 1.0
            v = vol_m.iloc[i - 1]
            if pd.isna(pas) or pd.isna(v) or v <= 0:
                continue
            pos[m.index[i]] = float(np.clip(np.sign(pas) * (VOL_OBJ / v),
                                            -TOPE, TOPE)) / DIVISOR
        if pos:
            ps = pd.Series(pos).sort_index()
            diarias[nom] = (ps.reindex(r_d.index, method="bfill") * r_d).dropna()
    DI = pd.DataFrame(diarias)
    return DI.sum(axis=1)[DI.notna().sum(axis=1) >= 6]

sc, sl = serie_trend(CORTO), serie_trend(LARGO)
C = pd.DataFrame({"corto": sc, "largo": sl}).dropna()
print(f"  {'version':<22}{'vol anual':>12}{'Sharpe':>10}{'peor dia':>11}")
print("  " + "-" * 55)
for c, nom in (("largo", f"vol de {LARGO} dias (especificacion)"),
               ("corto", f"vol de {CORTO} dias (lo que hay)")):
    x = C[c]
    print(f"  {nom:<22}{x.std()*np.sqrt(252):>12.2%}"
          f"{x.mean()/x.std()*np.sqrt(252):>10.2f}{x.min():>11.2%}")
print(f"\n  correlacion entre las dos series: {C['corto'].corr(C['largo']):.4f}")
print(f"  diferencia de Sharpe: "
      f"{C['corto'].mean()/C['corto'].std()*np.sqrt(252) - C['largo'].mean()/C['largo'].std()*np.sqrt(252):+.3f}")

print()
print(E)
print("C) ¿CADA CUANTO CAMBIA EL SIGNO? (cuanto puede envejecer el fichero)")
print(E)
print(f"  {'mercado':<11}{'meses':>8}{'cambios de signo':>18}"
      f"{'uno cada N meses':>19}{'% del tiempo largo':>20}")
print("  " + "-" * 74)
tot_cambios, tot_meses = 0, 0
for nom, s in series.items():
    m = s.resample("ME").last()
    sig = []
    for i in range(13, len(m)):
        pas = m.iloc[i - 1] / m.iloc[i - 13] - 1.0
        if not pd.isna(pas):
            sig.append(1 if pas >= 0 else -1)
    sig = np.array(sig)
    cambios = int((np.diff(sig) != 0).sum())
    tot_cambios += cambios
    tot_meses += len(sig)
    print(f"  {nom:<11}{len(sig):>8}{cambios:>18}"
          f"{len(sig)/max(cambios,1):>19.1f}{(sig > 0).mean():>20.0%}")
print("  " + "-" * 74)
print(f"  {'CONJUNTO':<11}{tot_meses:>8}{tot_cambios:>18}"
      f"{tot_meses/tot_cambios:>19.1f}")

print()
print(E)
print("D) ¿QUE PASA SI EL FICHERO DE SEÑALES SE QUEDA VIEJO?")
print(E)
print("  Se compara la cartera correcta contra usar la señal de hace N meses.")
print()
print(f"  {'retraso':>9}{'Sharpe':>10}{'vol':>9}{'% señales correctas':>21}")
print("  " + "-" * 49)


def serie_con_retraso(retraso):
    diarias = {}
    for nom, s in series.items():
        r_d = s.pct_change().dropna()
        vol = r_d.rolling(CORTO).std(ddof=1) * np.sqrt(252)
        m = s.resample("ME").last()
        vol_m = vol.resample("ME").last()
        pos = {}
        for i in range(13 + retraso, len(m)):
            j = i - retraso
            pas = m.iloc[j - 1] / m.iloc[j - 13] - 1.0
            v = vol_m.iloc[i - 1]
            if pd.isna(pas) or pd.isna(v) or v <= 0:
                continue
            pos[m.index[i]] = float(np.clip(np.sign(pas) * (VOL_OBJ / v),
                                            -TOPE, TOPE)) / DIVISOR
        if pos:
            ps = pd.Series(pos).sort_index()
            diarias[nom] = (ps.reindex(r_d.index, method="bfill") * r_d).dropna()
    DI = pd.DataFrame(diarias)
    return DI.sum(axis=1)[DI.notna().sum(axis=1) >= 6]


base = None
for ret in (0, 1, 2, 3, 6):
    x = serie_con_retraso(ret).dropna()
    if base is None:
        base = x
    al = pd.DataFrame({"b": base, "x": x}).dropna()
    sh = x.mean() / x.std() * np.sqrt(252)
    # % de señales que coinciden con la sin retraso
    coincide = "-" if ret == 0 else ""
    print(f"  {ret:>7} m{sh:>10.2f}{x.std()*np.sqrt(252):>9.2%}", end="")
    if ret == 0:
        print(f"{'100% (referencia)':>21}")
    else:
        # aproximacion: fraccion de meses en que el signo retrasado coincide
        acum, n = 0, 0
        for nom, s in series.items():
            m = s.resample("ME").last()
            sg = []
            for i in range(13, len(m)):
                pas = m.iloc[i - 1] / m.iloc[i - 13] - 1.0
                sg.append(1 if pas >= 0 else -1)
            sg = np.array(sg)
            if len(sg) > ret:
                acum += (sg[ret:] == sg[:-ret]).sum()
                n += len(sg) - ret
        print(f"{acum/n:>21.0%}")
