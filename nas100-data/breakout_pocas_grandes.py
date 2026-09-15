"""
¿TIENE VENTAJA LA SEÑAL DE EA_pocas_grandes_FTMO_US100?

La pregunta que hay que contestar ANTES de hablar de integrarlo con nada. El
codigo del EA es cuidadoso con las reglas de FTMO, pero en ningun sitio
demuestra que la señal gane dinero. De hecho su propio comentario v1.03 lo
admite: "bajar el riesgo NO crea ventaja estadistica. Si la expectativa por
operacion es negativa, reducir el tamaño solo hace que pierdas mas despacio."

Se replica la señal EXACTA leida del codigo:
  - velas M5 reconstruidas desde M1
  - canal = maximo/minimo de las 48 velas ANTERIORES a la ultima cerrada
  - señal larga si el cierre de la ultima vela cerrada supera el maximo
  - señal corta si perfora el minimo
  - entrada a mercado en la vela siguiente
  - stop 100 bp, objetivo 1R (100 bp)
  - maximo 2 entradas por dia
  - sin salida por tiempo (el EA no la tiene)

HIPOTESIS REGISTRADA ANTES DE MIRAR: un sistema de ruptura gana por la cola
derecha (pocas operaciones muy grandes). Truncar en 1R corta esa cola y deja
las perdidas enteras, que es la peor configuracion posible para una ruptura.
Espero expectativa NEGATIVA en 1R y menos negativa (o positiva) al ampliar el
objetivo. Si sale al contrario, desconfio de mi mismo antes de creerlo.

Coste: spread real medido de NACUSD.c = 1,37 bp, aplicado en la entrada.
"""
import glob, os
import numpy as np
import pandas as pd

DIR = "raw"
CANAL = 48
STOP_BP = 100.0
MAX_DIA = 2
SPREAD_BP = 1.37
MULTIPLOS = (1.0, 1.5, 2.0, 3.0, 5.0)

print("leyendo M1 y construyendo M5 ...")
trozos = []
for p in sorted(glob.glob(os.path.join(DIR, "*.csv"))):
    d = pd.read_csv(p)
    trozos.append(d)
M = pd.concat(trozos, ignore_index=True)
M["t"] = pd.to_datetime(M["timestamp"], unit="ms")
M = M[M["close"] > 0].drop_duplicates(subset="t").sort_values("t").reset_index(drop=True)
print(f"  barras M1: {len(M):,}  de {M['t'].iloc[0]} a {M['t'].iloc[-1]}")

# --- M5 por agrupacion de 5 minutos
M["b5"] = M["t"].dt.floor("5min")
g = M.groupby("b5")
M5 = pd.DataFrame({
    "high": g["high"].max(),
    "low":  g["low"].min(),
    "close": g["close"].last(),
    "n": g["close"].size(),
}).reset_index()
M5 = M5[M5["n"] >= 3].reset_index(drop=True)      # velas con datos suficientes
print(f"  barras M5: {len(M5):,}")

hi = M5["high"].values
lo = M5["low"].values
cl = M5["close"].values
tt = M5["b5"].values

# --- canal de las 48 velas ANTERIORES a la ultima cerrada
ser_hi = pd.Series(hi)
ser_lo = pd.Series(lo)
canal_hi = ser_hi.rolling(CANAL).max().shift(1).values
canal_lo = ser_lo.rolling(CANAL).min().shift(1).values

largo = (cl > canal_hi)
corto = (cl < canal_lo)
señal = np.where(largo, 1, np.where(corto, -1, 0))
idx_señal = np.where(señal != 0)[0]
print(f"  rupturas brutas: {len(idx_señal):,}")

# --- limite de 2 por dia
m1_t = M["t"].values
m1_hi = M["high"].values
m1_lo = M["low"].values
m1_cl = M["close"].values
# indice del primer M1 posterior al cierre de cada vela M5
fin_m5 = (M5["b5"] + pd.Timedelta(minutes=5)).values
pos_entrada = np.searchsorted(m1_t, fin_m5, side="left")

dias = M5["b5"].dt.floor("D").values
usados = {}
ops = []
for k in idx_señal:
    d = dias[k]
    if usados.get(d, 0) >= MAX_DIA:
        continue
    pe = pos_entrada[k]
    if pe >= len(m1_cl):
        continue
    usados[d] = usados.get(d, 0) + 1
    ops.append((k, pe, int(señal[k])))
print(f"  operaciones tras el limite de {MAX_DIA}/dia: {len(ops):,}")

# --- resolucion de barreras sobre M1
MAX_BARRAS = 60 * 24 * 10          # techo de 10 dias de M1


def resolver(mult):
    res = np.full(len(ops), np.nan)
    for j, (k, pe, dir_) in enumerate(ops):
        ent = m1_cl[pe - 1] if pe > 0 else m1_cl[pe]
        ent = ent * (1.0 + dir_ * SPREAD_BP / 1e4 / 2.0)    # media horquilla
        sl = ent * (1.0 - dir_ * STOP_BP / 1e4)
        tp = ent * (1.0 + dir_ * STOP_BP * mult / 1e4)
        fin = min(pe + MAX_BARRAS, len(m1_cl))
        h = m1_hi[pe:fin]; l = m1_lo[pe:fin]
        if dir_ > 0:
            toca_sl = l <= sl
            toca_tp = h >= tp
        else:
            toca_sl = h >= sl
            toca_tp = l <= tp
        i_sl = np.argmax(toca_sl) if toca_sl.any() else 10**9
        i_tp = np.argmax(toca_tp) if toca_tp.any() else 10**9
        if i_sl == 10**9 and i_tp == 10**9:
            res[j] = dir_ * (m1_cl[fin - 1] / ent - 1.0) * 1e4
        elif i_sl <= i_tp:                       # empate -> gana el stop
            res[j] = -STOP_BP
        else:
            res[j] = STOP_BP * mult
    return res


E = "=" * 92
print()
print(E)
print("EXPECTATIVA DE LA SEÑAL, POR MULTIPLO DE OBJETIVO")
print(E)
print(f"  {'objetivo':>9}{'n':>7}{'aciertos':>10}{'exp. bp':>10}{'desv.':>9}"
      f"{'t':>8}{'exp. % cuenta':>15}{'anual $ (10K)':>15}")
print("  " + "-" * 84)
anios = (M5["b5"].iloc[-1] - M5["b5"].iloc[0]).days / 365.25
for m in MULTIPLOS:
    r = resolver(m)
    r = r[~np.isnan(r)]
    exp = r.mean()
    t = exp / r.std() * np.sqrt(len(r))
    # riesgo 1,25% de la cuenta por 100 bp de stop
    pct = exp / STOP_BP * 1.25
    anual = pct / 100.0 * 10_000 * (len(r) / anios)
    gan = (r > 0).mean()
    print(f"  {m:>8.1f}R{len(r):>7}{gan:>10.1%}{exp:>10.2f}{r.std():>9.1f}"
          f"{t:>8.2f}{pct:>14.3f}%{anual:>14,.0f}$")

print()
print(E)
print("VEREDICTO")
print(E)
r1 = resolver(1.0)
r1 = r1[~np.isnan(r1)]
print(f"  Con la configuracion del EA (1R, que es la que trae por defecto):")
print(f"     operaciones en {anios:.1f} años : {len(r1):,}  "
      f"({len(r1)/anios:.0f} al año)")
print(f"     tasa de acierto            : {(r1>0).mean():.1%}  "
      f"(hace falta >50% para empatar a 1R)")
print(f"     expectativa por operacion  : {r1.mean():+.2f} bp")
print(f"     t de la expectativa        : {r1.mean()/r1.std()*np.sqrt(len(r1)):+.2f}")
print(f"     a 1,25% de riesgo, al año  : "
      f"{r1.mean()/STOP_BP*1.25/100*10_000*(len(r1)/anios):+,.0f} $ sobre 10K")
