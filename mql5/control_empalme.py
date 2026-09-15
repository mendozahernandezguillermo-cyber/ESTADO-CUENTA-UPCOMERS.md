#!/usr/bin/env python3
"""
CONTROL POSITIVO DEL EMPALME DE LA SEÑAL.

Replica en Python la logica EXACTA que acabo de escribir en MQL5, incluida la
tabla de referencia embebida, y predice lo que el informe del EA debe decir.

Simula la situacion real del broker: barras MN1 solo desde enero de 2026.
"""
import re
import numpy as np
import pandas as pd

# ---------------------------------------------- leer la tabla embebida
txt = open("EA_Trend_Multi.mq5", encoding="utf-8").read()

def bloque(nombre):
    i = txt.index(nombre)
    j = txt.index("{", i)
    k = txt.index("};", j)
    return txt[j + 1:k]

REF_ANIOMES = [int(x) for x in re.findall(r"\d{6}", bloque("int REF_ANIOMES"))]
REF_SIMBOLO = re.findall(r'"([^"]+)"', bloque("string REF_SIMBOLO"))
crudo = bloque("double REF_CIERRE")
crudo = re.sub(r"//[^\n]*", "", crudo)
REF_CIERRE = [float(x) for x in re.findall(r"-?\d+\.\d+", crudo)]

NM, NS = len(REF_ANIOMES), len(REF_SIMBOLO)
assert len(REF_CIERRE) == NM * NS, \
    f"REF_CIERRE tiene {len(REF_CIERRE)}, esperaba {NM*NS}"
print(f"tabla embebida leida: {NS} mercados x {NM} meses = {len(REF_CIERRE)} valores")
print(f"meses: {REF_ANIOMES[0]} .. {REF_ANIOMES[-1]}")
print(f"simbolos: {', '.join(REF_SIMBOLO)}")


def aniomes_menos(a, k):
    y, m = a // 100, a % 100
    tot = y * 12 + (m - 1) - k
    return (tot // 12) * 100 + (tot % 12 + 1)


def cierre_ref(idx, aniomes):
    for i, am in enumerate(REF_ANIOMES):
        if am == aniomes:
            return REF_CIERRE[idx * NM + i]
    return -1.0


# ---------------------------------------------- serie "del broker"
# El broker solo tiene desde enero de 2026. Como referencia y broker salen de
# la misma fuente en este control, el factor de empalme debe salir 1.0000 y el
# retorno reconstruido debe coincidir EXACTAMENTE con el real. Si no coincide,
# el empalme esta mal planteado.
FUENTES = {
    "SPCUSD.c": "../trend/datos/SPY.csv",
    "NACUSD.c": "../trend/datos/QQQ.csv",
    "XAUUSD":   "../trend/datos/GLD.csv",
    "XAGUSD":   "../trend/datos/SLV.csv",
    "EURUSD":   "../trend/datos/EURUSDX.csv",
    "USDJPY":   "../trend/datos/USDJPYX.csv",
    "GBPUSD":   "../trend/datos/GBPUSDX.csv",
    "AUDUSD":   "../trend/datos/AUDUSDX.csv",
}
MIRADA = 12
ANIOMES0 = 202609        # mes en curso: septiembre de 2026
PRIMER_MES_BROKER = 202601

print()
print("=" * 88)
print("CONTROL 1: con la MISMA fuente, el empalme debe ser exacto")
print("=" * 88)
print(f"  mes en curso {ANIOMES0}  ·  el broker solo tiene desde "
      f"{PRIMER_MES_BROKER}")
nb = (ANIOMES0 // 100 * 12 + ANIOMES0 % 100) - \
     (PRIMER_MES_BROKER // 100 * 12 + PRIMER_MES_BROKER % 100) + 1
print(f"  -> barras MN1 disponibles: {nb}   (indice 0..{nb-1})")
idx_nec = MIRADA + 1
idx_solape = nb - 1
print(f"  -> se necesita el indice {idx_nec} y el mas antiguo es {idx_solape}"
      f"  => HAY QUE EMPALMAR")
print()
print(f"  {'mercado':<11}{'solape':>8}{'factor':>9}{'mes -13':>9}"
      f"{'p13 empalmado':>15}{'p13 real':>11}{'error':>9}{'señal':>7}")
print("  " + "-" * 79)

resultados = {}
for k, sim in enumerate(REF_SIMBOLO):
    d = pd.read_csv(FUENTES[sim], index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    m = s[s > 0].resample("ME").last().dropna()
    porma = {dt.year * 100 + dt.month: v for dt, v in m.items()}

    am1 = aniomes_menos(ANIOMES0, 1)
    am_solape = aniomes_menos(ANIOMES0, idx_solape)
    am13 = aniomes_menos(ANIOMES0, idx_nec)

    broker_solape = porma[am_solape]
    factor = broker_solape / cierre_ref(k, am_solape)
    p13_emp = cierre_ref(k, am13) * factor
    p13_real = porma[am13]
    p1 = porma[am1]
    r = p1 / p13_emp - 1.0
    err = p13_emp / p13_real - 1.0
    resultados[sim] = (r, 1 if r >= 0 else -1)
    print(f"  {sim:<11}{am_solape:>8}{factor:>9.4f}{am13:>9}"
          f"{p13_emp:>15.4f}{p13_real:>11.4f}{err:>+9.2%}"
          f"{(1 if r >= 0 else -1):>7}")

print()
print("  El factor debe ser 1.0000 y el error 0.00% en los ocho: aqui la")
print("  referencia y el 'broker' son la misma serie. Cualquier desviacion")
print("  seria un error de indexado de meses.")

# ---------------------------------------------- control 2: robustez
print()
print("=" * 88)
print("CONTROL 2: ¿aguanta el empalme si el broker cotiza a otro NIVEL?")
print("=" * 88)
print("  Se multiplica la serie del broker por 10 (como SPY frente al S&P).")
print("  El retorno de 12 meses NO debe cambiar ni un punto basico.")
print()
print(f"  {'mercado':<11}{'ret 12m normal':>17}{'ret 12m con x10':>18}"
      f"{'diferencia':>13}")
print("  " + "-" * 59)
for k, sim in enumerate(REF_SIMBOLO):
    d = pd.read_csv(FUENTES[sim], index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    m = s[s > 0].resample("ME").last().dropna()
    porma = {dt.year * 100 + dt.month: v for dt, v in m.items()}

    am1 = aniomes_menos(ANIOMES0, 1)
    am_solape = aniomes_menos(ANIOMES0, idx_solape)
    am13 = aniomes_menos(ANIOMES0, idx_nec)

    def ret(esc):
        f = (porma[am_solape] * esc) / cierre_ref(k, am_solape)
        return (porma[am1] * esc) / (cierre_ref(k, am13) * f) - 1.0

    r1, r10 = ret(1.0), ret(10.0)
    print(f"  {sim:<11}{r1:>+17.4%}{r10:>+18.4%}{(r10-r1)*1e4:>+11.2f} bp")

# ---------------------------------------------- prediccion final
print()
print("=" * 88)
print("PREDICCION DEL INFORME (equity 24.604,63 · vol de 150 dias del broker)")
print("=" * 88)
EQUITY = 24604.63
VOL_OBJ = 7.23 / 100.0
TOPE, DIVISOR, DIAS_VOL = 5.0, 8, 150
print(f"  {'mercado':<11}{'ret 12m':>10}{'señal':>7}{'vol 150d':>10}"
      f"{'exposicion':>12}{'nocional':>11}")
print("  " + "-" * 61)
bruta = 0.0
for k, sim in enumerate(REF_SIMBOLO):
    d = pd.read_csv(FUENTES[sim], index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    s = s[s > 0]
    r_d = s.pct_change().dropna().iloc[-DIAS_VOL:]
    vol = r_d.std(ddof=1) * np.sqrt(252)
    r, senal = resultados[sim]
    e = senal * min(VOL_OBJ / vol, TOPE) / DIVISOR
    bruta += abs(e)
    print(f"  {sim:<11}{r:>+9.1%}{senal:>7}{vol:>9.1%}{e:>+11.2%}"
          f"{abs(e)*EQUITY:>11,.0f}")
print("  " + "-" * 61)
print(f"  exposicion bruta total: {bruta:.1%} de la equity")
