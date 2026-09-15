#!/usr/bin/env python3
"""
RESTRICCION: la prop firm NO permite mantener posiciones en FIN DE SEMANA.

Afecta a las dos estrategias de forma muy distinta y hay que medirlo, no
suponerlo:

  #1 pre-FOMC : el anuncio cae en dia de semana y la posicion se abre la tarde
                anterior. Si nunca cruza un sabado, la restriccion NO la toca.
                Se verifica sobre las 212 fechas reales.

  #2 trend    : mantiene posiciones un mes entero, asi que cruza ~4 fines de
                semana al mes. Para cumplir la regla habria que cerrar el
                viernes y reabrir el lunes, lo que cuesta dos cosas:
                  - el retorno del hueco del fin de semana (cierre del viernes
                    a apertura del lunes)
                  - dos transacciones extra por mercado y por semana
                Se mide cuanto cuesta cada cosa.
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

DIRT = "../trend/datos"

# ==================================================== #1: ¿cruza fin de semana?
EXCL = {pd.Timestamp(x).date() for x in
        ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"]}
f = pd.read_csv("../fomc/fomc_fechas.csv", parse_dates=["fecha"])
F = f[~f["fecha"].dt.date.isin(EXCL)]["fecha"]

print("=" * 84)
print("#1 PRE-FOMC · ¿la posicion cruza alguna vez un fin de semana?")
print("=" * 84)
DOW = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
vc = F.dt.dayofweek.value_counts().sort_index()
print("  dia de la semana del ANUNCIO (n=%d):" % len(F))
for d, n in vc.items():
    print("     %-11s %3d  (%.1f%%)  %s" % (DOW[d], n, 100 * n / len(F),
                                            "#" * int(40 * n / vc.max())))
# la posicion se abre el dia de mercado anterior. cruza fin de semana solo si
# el anuncio es LUNES (se abriria el viernes)
lunes = int((F.dt.dayofweek == 0).sum())
print()
print("  anuncios en LUNES (la posicion se abriria el viernes): %d" % lunes)
if lunes == 0:
    print("  -> la #1 NUNCA cruza un fin de semana. La restriccion NO la afecta.")
else:
    print("  -> %d eventos habria que saltarse (%.1f%% del total)"
          % (lunes, 100 * lunes / len(F)))

# ==================================================== #2: coste del cierre
UNIV = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV",
        "EURUSDX", "USDJPYX", "GBPUSDX", "AUDUSDX"]
VOL_OBJ, MIRADA = 0.10, 12

datos = {}
for tk in UNIV:
    p = "%s/%s.csv" % (DIRT, tk)
    if not os.path.exists(p):
        continue
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    d = d[["Open", "Close"]].dropna()
    d = d[(d > 0).all(axis=1)]
    datos[tk] = d

con, sin, giro_extra = {}, {}, {}
for tk, d in datos.items():
    c = d["Close"]
    r_cc = c.pct_change()                          # cierre a cierre
    r_oc = d["Close"] / d["Open"] - 1.0            # apertura a cierre
    es_lunes = d.index.dayofweek == 0
    # sin exposicion de fin de semana: los lunes solo se captura open->close
    r_sin = r_cc.where(~es_lunes, r_oc)

    vol = (r_cc.rolling(252).std() * np.sqrt(252)).resample("ME").last()
    m = c.resample("ME").last()
    pos_m = {}
    for i in range(MIRADA + 1, len(m)):
        pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
        v = vol.iloc[i - 1]
        if pd.isna(pas) or pd.isna(v) or v <= 0:
            continue
        pos_m[m.index[i]] = np.clip(np.sign(pas) * (VOL_OBJ / v), -5, 5)
    if not pos_m:
        continue
    ps = pd.Series(pos_m)
    pos_d = ps.reindex(r_cc.index, method="bfill")
    pos_d = pos_d.where(pos_d.index <= ps.index.max())
    con[tk] = (pos_d * r_cc).dropna()
    sin[tk] = (pos_d * r_sin).dropna()
    # transacciones extra: se cierra el viernes y se reabre el lunes
    giro_extra[tk] = (pos_d.abs() * (d.index.dayofweek == 4)).dropna()

CON = pd.DataFrame(con)
SIN = pd.DataFrame(sin)
GX = pd.DataFrame(giro_extra)
n_ok = CON.notna().sum(axis=1)
r_con = CON.mean(axis=1)[n_ok >= 6]
r_sin = SIN.mean(axis=1)[n_ok >= 6]
gx = GX.mean(axis=1).reindex(r_con.index).fillna(0.0)

print()
print("=" * 84)
print("#2 TREND · COSTE DE CERRAR TODOS LOS VIERNES")
print("=" * 84)


def resu(r, per=252):
    mu, sd = r.mean() * per, r.std() * np.sqrt(per)
    return dict(mu=mu, sd=sd, sh=mu / sd if sd else np.nan,
                t=r.mean() / r.std() * np.sqrt(len(r)))


a, b = resu(r_con), resu(r_sin)
print(f"{'':<28}{'retorno':>10}{'vol':>9}{'Sharpe':>9}{'t':>7}")
print("-" * 84)
print(f"{'con exposicion fin de sem.':<28}{a['mu']:>9.2%}{a['sd']:>9.2%}"
      f"{a['sh']:>9.2f}{a['t']:>7.2f}")
print(f"{'SIN exposicion (plano vie)':<28}{b['mu']:>9.2%}{b['sd']:>9.2%}"
      f"{b['sh']:>9.2f}{b['t']:>7.2f}")
print()
print("  retorno perdido por no tener el hueco del fin de semana: %.2f%%/año"
      % ((a["mu"] - b["mu"]) * 100))
print("  fraccion del retorno que estaba en el fin de semana: %.0f%%"
      % (100 * (a["mu"] - b["mu"]) / a["mu"]) if a["mu"] else 0)

print()
print("  transacciones extra: %.3f de exposicion por semana y mercado"
      % gx[gx > 0].mean())
print()
print(f"  {'coste ida (bp)':>16}{'coste anual':>14}{'Sharpe neto':>14}")
print("  " + "-" * 46)
for bp in (1, 2, 5, 10):
    # cerrar viernes + reabrir lunes = 2 transacciones sobre la exposicion
    coste_d = gx * 2 * bp / 1e4
    neto = (r_sin - coste_d).dropna()
    x = resu(neto)
    print(f"  {bp:>16}{(coste_d.sum()/len(coste_d)*252)*100:>13.2f}%"
          f"{x['sh']:>14.2f}")

print()
print("=" * 84)
print("VEREDICTO")
print("=" * 84)
print("  #1 pre-FOMC : %s"
      % ("NO afectada, nunca cruza fin de semana" if lunes == 0
         else "afectada en %d de %d eventos" % (lunes, len(F))))
print("  #2 trend    : Sharpe %.2f -> %.2f sin el fin de semana, antes de costes"
      % (a["sh"], b["sh"]))
for bp in (2, 5):
    x = resu((r_sin - gx * 2 * bp / 1e4).dropna())
    print("                con coste de %d bp por transaccion: Sharpe %.2f"
          % (bp, x["sh"]))
