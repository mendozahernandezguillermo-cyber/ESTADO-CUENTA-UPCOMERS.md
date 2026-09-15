"""
"UPCOMERS TARDA AÑOS, ASI QUE MEJOR FTMO" -- ¿ES CIERTO EL 'ASI QUE'?

La conclusion de ir a FTMO puede ser buena, pero no por esta razon. En FTMO hay
que escalar +10% y luego +5% ANTES de cobrar un dolar. En Upcomers cobras en
cuanto tienes +1% y 6 dias cualificados. Asi que a priori FTMO deberia tardar
MAS en dar el primer dolar, no menos, y solo compensar despues.

Se mide la unica cosa que compara los dos vehiculos de forma honesta:
la fecha del PRIMER DINERO QUE LLEGA AL BOLSILLO, y la probabilidad acumulada
de haber cobrado algo a los 12, 24 y 36 meses.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]

np_ = ns["__name__"]
pi = {"__name__": "pipe"}
exec(compile(open("ftmo_pipeline.py", encoding="utf-8")
             .read().split('E = "=" * 96')[0], "ftmo_pipeline.py", "exec"), pi)
caminos = pi["caminos"]
CUENTA = pi["CUENTA"]; CUOTA_F = pi["CUOTA"]; OBJ = pi["OBJ"]
MAXLOSS, DAILY = pi["MAXLOSS"], pi["DAILY"]
MIN_MERCADO, SPLIT, CICLO = pi["MIN_MERCADO"], pi["SPLIT"], pi["CICLO"]
RNG = pi["RNG"]; SUB = pi["SUB"]

N = 20_000
ANIOS = 3
DIAS = 252 * ANIOS


def pipeline_fechado(x1, x2, sd, dias):
    """igual que el pipeline de FTMO pero anotando el dia del PRIMER cobro"""
    n = x1.shape[0]
    est = np.zeros(n, int); bal = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - MAXLOSS))
    dfase = np.zeros(n, int); ult = np.zeros(n, int)
    recibido = np.zeros(n); pagado = np.full(n, CUOTA_F)
    ncob = np.zeros(n, int); d1 = np.full(n, -1)
    paso0 = sd / np.sqrt(SUB)
    for d in range(dias):
        ini = bal.copy()
        pdia = np.maximum(piso, ini - CUENTA * DAILY)   # regla real de FTMO
        eq = ini + ini * x1[:, d]
        b = RNG.normal(0.0, paso0, size=(n, SUB)).cumsum(axis=1)
        k = np.arange(1, SUB + 1) / SUB
        br = (b - k[None, :] * b[:, -1:]) + k[None, :] * x2[:, d][:, None]
        cam = eq[:, None] + ini[:, None] * br
        rompe = (eq < pdia) | (cam < pdia[:, None]).any(1)
        r = np.where(rompe)[0]
        if r.size:
            est[r] = 0; bal[r] = CUENTA
            piso[r] = CUENTA * (1 - MAXLOSS)
            dfase[r] = 0; ult[r] = d; pagado[r] += CUOTA_F
        v = np.where(~rompe)[0]
        bal[v] = cam[~rompe, -1]; dfase[v] += 1
        reto = v[est[v] < 2]
        if reto.size:
            ok = reto[(bal[reto] >= CUENTA * (1 + OBJ[est[reto]]))
                      & (dfase[reto] >= MIN_MERCADO)]
            if ok.size:
                est[ok] += 1; bal[ok] = CUENTA
                piso[ok] = CUENTA * (1 - MAXLOSS)
                dfase[ok] = 0; ult[ok] = d
        fon = v[est[v] == 2]
        if fon.size:
            pide = fon[(bal[fon] > CUENTA) & (d - ult[fon] >= CICLO)]
            if pide.size:
                recibido[pide] += (bal[pide] - CUENTA) * SPLIT
                bal[pide] = CUENTA; ult[pide] = d; ncob[pide] += 1
                d1[pide] = np.where(d1[pide] < 0, d, d1[pide])
    return dict(recibido=recibido, d1=d1, ncob=ncob, pagado=pagado,
                neto=recibido + np.where(ncob > 0, CUOTA_F, 0.0) - pagado)


E = "=" * 96
print(E)
print(f"¿CUANDO LLEGA EL PRIMER DOLAR AL BOLSILLO?  ({ANIOS} años simulados)")
print(E)
print(f"  {'vehiculo':<30}{'1er cobro':>11}{'en meses':>10}"
      f"{'a 12m':>9}{'a 24m':>9}{'a 36m':>9}{'EV/año':>10}")
print("  " + "-" * 88)

filas = []
# ---- Upcomers, TP 40 y TP 50
for tp in (50.0, 40.0):
    x1, x2, _ = preparar(tp)
    g1, g2 = mod["bootstrap_par"](x1, x2, DIAS, N)
    r = simular2(g1, g2, x2.std())
    d1 = r["d1"]
    med = np.median(d1[d1 >= 0]) if (d1 >= 0).any() else np.nan
    filas.append((f"Upcomers · vol 4,5% · TP {int(tp)}", med,
                  [((d1 >= 0) & (d1 <= 252 * a)).mean() for a in (1, 2, 3)],
                  r["neto"].mean() / ANIOS))

# ---- FTMO a distintas vol
for vol in (0.045, 0.08, 0.10):
    x1, x2, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, DIAS, N)
    r = pipeline_fechado(g1, g2, x2.std(), DIAS)
    d1 = r["d1"]
    med = np.median(d1[d1 >= 0]) if (d1 >= 0).any() else np.nan
    filas.append((f"FTMO 2-Step · vol {vol:.1%}", med,
                  [((d1 >= 0) & (d1 <= 252 * a)).mean() for a in (1, 2, 3)],
                  r["neto"].mean() / ANIOS))

for nom, med, acum, ev in filas:
    print(f"  {nom:<30}{(med if not np.isnan(med) else -1):>10.0f}d"
          f"{(med/21 if not np.isnan(med) else float('nan')):>9.1f}m"
          f"{acum[0]:>9.1%}{acum[1]:>9.1%}{acum[2]:>9.1%}{ev:>9,.0f}$")

print()
print(E)
print("LO QUE ESTA TABLA DICE")
print(E)
u = filas[1]; f45 = filas[2]; f8 = filas[3]
print(f"  Upcomers TP 40 da el primer dolar en {u[1]:.0f} dias ({u[1]/21:.1f} meses).")
print(f"  FTMO a la MISMA vol lo da en {f45[1]:.0f} dias ({f45[1]/21:.1f} meses).")
print(f"  FTMO a vol 8% lo da en {f8[1]:.0f} dias ({f8[1]/21:.1f} meses).")
print()
print("  O sea: FTMO NO acorta la espera. La alarga. Lo que hace es pagar mucho")
print("  mas cuando por fin paga, porque no tiene topes. Cambiar a FTMO porque")
print("  'Upcomers tarda años' es cambiarse al vehiculo que tarda MAS.")
print("  El argumento bueno para FTMO es otro: el tamaño del cobro, no la fecha.")
