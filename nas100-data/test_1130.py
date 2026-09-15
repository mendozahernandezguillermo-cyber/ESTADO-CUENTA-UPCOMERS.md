#!/usr/bin/env python3
"""
TEST PRE-REGISTRADO

Hipotesis, derivada EXCLUSIVAMENTE de los timestamps reales de joxemi
(endpoint publico de journal de THL, 581 entradas de NASDAQ 2025-2026):

    Entrar LARGO en NASDAQ a las 11:30 hora de Nueva York
    y mantener 82 minutos.

Justificacion externa a los datos de precio:
  - 68 de 581 entradas (11.7%) caen en ese unico minuto
  - de ellas el 77.9% son largas (frente al 62.2% del resto)
  - duracion mediana en ese slot: 82 minutos
  - el 95.3% de todas sus entradas tienen segundo=00 y el 92% caen en
    multiplos de 5 min -> evalua en cierres de vela M5

Esto es UNA sola prueba. La hipotesis no se ha extraido de los precios,
asi que no hay que corregir por pruebas multiples sobre ellos.

El barrido de las 288 franjas del dia que aparece despues NO es la
prueba: es contexto para saber si las 11:30 destacan o son un dia
cualquiera a media sesion. Se lee con la correccion correspondiente.

LIMITACION CONOCIDA: estos datos son el indice cash (Dukascopy
usatechidxusd). joxemi opera el CFD "NASDAQ 100 (Mini)" de Darwinex,
derivado del futuro. Ya comprobamos que ambas series divergen. A las
11:30, en plena sesion cash, la divergencia deberia ser menor que en la
apertura, pero es una limitacion real y no se puede descartar.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

ENTRADA_NY = 11 * 60 + 30      # 11:30 NY  <- pre-registrado
HOLD_MIN = 82                  # 82 min    <- pre-registrado
COST_BP = 0.40


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    et = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(fecha=et.dt.date,
                   tod=et.dt.hour * 60 + et.dt.minute,
                   dow=et.dt.dayofweek)
    return df[df["dow"] < 5]


def sesiones(df):
    out = []
    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        # exige sesion cash razonablemente completa
        if ((tod >= 9 * 60 + 30) & (tod <= 16 * 60)).sum() < 300:
            continue
        out.append((fecha, tod, o, c))
    return out


def prueba(ses, entrada_min, hold, lo, hi):
    """Largo en 'entrada_min', salida 'hold' minutos despues."""
    r = []
    for fecha, tod, o, c in ses:
        if not (lo <= fecha.year <= hi):
            continue
        ia = np.where(tod >= entrada_min)[0]
        ib = np.where(tod >= entrada_min + hold)[0]
        if not len(ia) or not len(ib):
            continue
        # exige que la entrada este cerca del minuto pedido (sin huecos)
        if tod[ia[0]] > entrada_min + 5:
            continue
        p0 = o[int(ia[0])]
        p1 = o[int(ib[0])]
        if p0 <= 0:
            continue
        r.append((p1 / p0 - 1) * 1e4 - COST_BP)
    return np.array(r)


def linea(x, etq):
    n = len(x)
    if n < 30:
        print("  %-22s n=%d insuficiente" % (etq, n))
        return None
    t, p2 = stats.ttest_1samp(x, 0.0)
    p = p2 / 2 if t > 0 else 1 - p2 / 2
    # anualizado: ~252 oportunidades al ano
    anual = x.mean() * 252 / 100.0
    print("  %-22s n=%5d  media=%+7.2f bp  sd=%6.1f  t=%+6.2f  p=%.4f  "
          "acierto=%5.2f%%  anual=%+6.2f%%"
          % (etq, n, x.mean(), x.std(ddof=1), t, p,
             100.0 * (x > 0).mean(), anual))
    return dict(n=n, media=x.mean(), t=t, p=p)


def main():
    df = cargar()
    ses = sesiones(df)
    print("Sesiones: %d   (%s -> %s)" % (len(ses), ses[0][0], ses[-1][0]))
    print()
    print("=" * 100)
    print("  PRUEBA PRIMARIA PRE-REGISTRADA: LARGO a las 11:30 NY, "
          "mantener 82 min")
    print("=" * 100)
    for lo, hi, etq in [(2011, 2026, "1. TODO 2011-2026"),
                        (2011, 2019, "2. 2011-2019"),
                        (2020, 2024, "3. 2020-2024"),
                        (2025, 2026, "4. 2025-2026 (su epoca)")]:
        linea(prueba(ses, ENTRADA_NY, HOLD_MIN, lo, hi), etq)

    print()
    print("=" * 100)
    print("  CONTEXTO A: sensibilidad del tiempo de mantenimiento "
          "(muestra completa)")
    print("=" * 100)
    for h in [15, 30, 60, 82, 120, 180, 270]:
        linea(prueba(ses, ENTRADA_NY, h, 2011, 2026), "hold=%d min" % h)

    print()
    print("=" * 100)
    print("  CONTEXTO B: destacan las 11:30 frente al resto del dia?")
    print("  (288 franjas; con esa cantidad de pruebas el umbral de |t| "
          "sube a ~3.6)")
    print("=" * 100)
    filas = []
    for m in range(0, 1440, 5):
        x = prueba(ses, m, HOLD_MIN, 2011, 2026)
        if len(x) >= 500:
            t, p2 = stats.ttest_1samp(x, 0.0)
            filas.append((m, len(x), x.mean(), t))
    F = pd.DataFrame(filas, columns=["min", "n", "media", "t"])

    print("  Mejores 10 franjas del dia por t:")
    for _, r in F.sort_values("t", ascending=False).head(10).iterrows():
        mark = "  <-- 11:30" if int(r["min"]) == ENTRADA_NY else ""
        print("    %02d:%02d NY  n=%5d  media=%+7.2f bp  t=%+6.2f%s"
              % (int(r["min"]) // 60, int(r["min"]) % 60, r["n"],
                 r["media"], r["t"], mark))

    fila = F[F["min"] == ENTRADA_NY]
    if len(fila):
        rk = int((F["t"] > fila["t"].iloc[0]).sum()) + 1
        print()
        print("  Posicion de las 11:30 en el ranking: %d de %d franjas"
              % (rk, len(F)))
        print("  Percentil: %.1f" % (100.0 * (1 - rk / len(F))))
    print()
    print("  Distribucion de las t de las 288 franjas: "
          "media=%.2f  sd=%.2f  max=%.2f  min=%.2f"
          % (F["t"].mean(), F["t"].std(), F["t"].max(), F["t"].min()))
    print("  Si no hubiera nada, esas t serian ~N(0,1). "
          "sd observada = %.2f" % F["t"].std())

    F.to_csv(os.path.join(os.path.dirname(RAW), "franjas_dia.csv"),
             index=False)


if __name__ == "__main__":
    main()
