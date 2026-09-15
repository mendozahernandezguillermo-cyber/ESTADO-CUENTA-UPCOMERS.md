"""
AUDACITY CAPITAL FTP (INSTANT FUNDING) CONTRA UPCOMERS VANGUARD.

Reglas leidas en la fuente (audacity.capital/knowledge-center/ftp/ y zendesk):
  - diario 5% TRAILING sobre la MAXIMA EQUITY DEL DIA (suelo movil que sube y
    no baja), reinicio 00:00 hora servidor MT5 (GMT+3 mar-oct, GMT+2 nov-feb)
  - maxima 10% ESTATICA sobre el saldo inicial
  - se calcula sobre EQUITY, con posiciones abiertas dentro
  - "Payout Eligibility: You can request your payout once you reach a 10%
     profit milestone on your account"
  - retiradas cada 14 dias desde la activacion, pago el mismo dia
  - reparto hasta 80% (tabla del usuario) / hasta 90% (otra pagina) -> 80%
  - 5 dias minimos de trading, SIN regla de consistencia
  - inactividad: 6 MESES
  - cuentas de 5.000 a 50.000 $

DOS CORRECCIONES A LA PREMISA "no tiene bloqueos para pagos":
  1. El bloqueo es MAYOR, no menor: Upcomers deja cobrar con +1% de beneficio.
     Audacity exige +10%. Es diez veces mas alto.
  2. El "5% diario" NO es como el 4% de Upcomers. El de Upcomers es un suelo
     fijo calculado al inicio del dia. El de Audacity es un TRINQUETE que sube
     con la equity intradia y no vuelve a bajar.

Lo que SI es mejor, y es mucho:
  - sin topes por cobro y sin regla del mejor dia -> desaparece LA PINZA
  - suelo maximo 10% estatico en vez de 7% trailing
  - inactividad de 6 meses en vez de 35 dias -> el latido deja de ser critico

Se mide todo el pipeline. La cuota no aparece publicada, asi que se barre.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
mod = ns["mod"]; simular2 = ns["simular2"]
preparar = mod["preparar"]; RNG = mod["RNG"]
BLOQUE, SUB = mod["BLOQUE"], mod["SUB"]

CUENTA = 25_000.0
DD_MAX = 0.10          # estatico sobre el inicial
DD_DIA = 0.05          # TRAILING sobre el maximo del dia
HITO = 0.10            # +10% para poder cobrar
SPLIT = 0.80
CICLO = 14
MIN_DIAS = 5
N = 20_000


def caminos(x1, x2, dias, n):
    nb = int(np.ceil(dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n, -1)[:, :dias]
    return x1[idx], x2[idx]


def audacity(x1, x2, sd, dias, hito_repite=True):
    n = x1.shape[0]
    bal = np.full(n, CUENTA)
    piso = CUENTA * (1 - DD_MAX)          # estatico, no se mueve nunca
    vivo = np.ones(n, bool)
    ndias = np.zeros(n, int); ult = np.zeros(n, int)
    recibido = np.zeros(n); ncob = np.zeros(n, int)
    d1 = np.full(n, -1)
    hito_hecho = np.zeros(n, bool)
    n_trail = np.zeros(n, int)            # veces que mordio el trailing diario
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        act = np.where(vivo)[0]
        if act.size == 0:
            break
        ini = bal[act]
        eq0 = ini + ini * x1[act, d]

        b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
        k = np.arange(1, SUB + 1) / SUB
        br = (b - k[None, :] * b[:, -1:]) + k[None, :] * x2[act, d][:, None]
        cam = np.concatenate([eq0[:, None], eq0[:, None] + ini[:, None] * br], 1)

        # suelo diario TRAILING: 95% del maximo alcanzado hasta ese instante
        pico = np.maximum.accumulate(np.maximum(cam, ini[:, None]), axis=1)
        suelo_dia = pico * (1 - DD_DIA)
        rompe_dia = (cam < suelo_dia).any(1)
        rompe_max = (cam < piso).any(1)
        rompe = rompe_dia | rompe_max
        n_trail[act[rompe_dia & ~rompe_max]] += 1
        vivo[act[rompe]] = False

        v = act[~rompe]
        if v.size == 0:
            continue
        bal[v] = cam[~rompe, -1]
        ndias[v] += 1

        pide = v[(bal[v] >= CUENTA * (1 + HITO)) & (ndias[v] >= MIN_DIAS)
                 & (d - ult[v] >= CICLO)]
        if pide.size:
            recibido[pide] += (bal[pide] - CUENTA) * SPLIT
            bal[pide] = CUENTA
            ult[pide] = d
            ncob[pide] += 1
            hito_hecho[pide] = True
            d1[pide] = np.where(d1[pide] < 0, d, d1[pide])

    return dict(recibido=recibido, ncob=ncob, quemada=~vivo, d1=d1,
                n_trail=n_trail, bal=bal)


E = "=" * 96
print(E)
print("¿MUERDE EL TRAILING DIARIO DEL 5% A NUESTRA VOLATILIDAD?")
print(E)
print(f"  {'vol':>7}{'P(quema 4a)':>13}{'por trailing diario':>21}"
      f"{'por el 10% estatico':>21}")
print("  " + "-" * 64)
for vol in (0.045, 0.08, 0.12):
    x1, x2, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * 4, N)
    r = audacity(g1, g2, x2.std(), 252 * 4)
    p_tr = (r["n_trail"] > 0).mean()
    print(f"  {vol:>7.1%}{r['quemada'].mean():>13.1%}{p_tr:>20.1%}"
          f"{r['quemada'].mean()-p_tr:>20.1%}")
print()
print("  A 4,5% de vol anual la desviacion diaria es 0,28%. Un vuelco intradia")
print("  del 5% son ~18 sigmas: el trinquete diario suena temible y no muerde.")
print("  Lo que decide es el hito del +10%.")

print()
print(E)
print("PIPELINE COMPLETO A 4 AÑOS  ·  cuenta de 25.000 $  ·  reparto 80%")
print(E)
print(f"  {'vol':>7}{'P(cobra)':>10}{'1er cobro':>11}{'cobros':>8}"
      f"{'recibido':>11}{'por año':>10}{'P(quema)':>10}")
print("  " + "-" * 68)
mejor = None
for vol in (0.045, 0.06, 0.08, 0.10, 0.12):
    x1, x2, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * 4, N)
    r = audacity(g1, g2, x2.std(), 252 * 4)
    dd = r["d1"][r["d1"] >= 0]
    rec = r["recibido"].mean()
    print(f"  {vol:>7.1%}{(r['ncob']>0).mean():>10.1%}"
          f"{(np.median(dd) if dd.size else np.nan):>10.0f}d"
          f"{r['ncob'].mean():>8.2f}{rec:>10,.0f}${rec/4:>9,.0f}$"
          f"{r['quemada'].mean():>10.1%}")
    if mejor is None or rec > mejor[0]:
        mejor = (rec, vol)

print()
print(E)
print("COMPARACION A 4 AÑOS, MISMA ESTRATEGIA, CUENTA DE 25.000 $")
print(E)
x1, x2, _ = preparar(40.0)
g1, g2 = mod["bootstrap_par"](x1, x2, 252 * 4, N)
up = simular2(g1, g2, x2.std())
print(f"  {'vehiculo':<40}{'recibido 4a':>14}{'por año':>10}{'1er cobro':>12}")
print("  " + "-" * 78)
print(f"  {'Upcomers Vanguard · vol 4,5% · TP 40':<40}"
      f"{up['recibido'].mean():>13,.0f}${up['recibido'].mean()/4:>9,.0f}$"
      f"{np.median(up['d1'][up['d1']>=0]):>11.0f}d")
for vol in (0.045, 0.08):
    x1, x2, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * 4, N)
    r = audacity(g1, g2, x2.std(), 252 * 4)
    dd = r["d1"][r["d1"] >= 0]
    print(f"  {'Audacity FTP · vol %.1f%%' % (vol*100):<40}"
          f"{r['recibido'].mean():>13,.0f}${r['recibido'].mean()/4:>9,.0f}$"
          f"{(np.median(dd) if dd.size else np.nan):>11.0f}d")
print()
print("  (sin restar cuota: Audacity no publica el precio del FTP. Hay que")
print("   preguntarlo y restarlo; a 25K, cada 100 $ de cuota son 25 $/año.)")
