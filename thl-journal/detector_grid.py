#!/usr/bin/env python3
"""
DETECTOR DE MARTINGALA / GRID sobre el journal publico de Darwinex.

Semantica de campos fijada empiricamente en semantica.py:
  c2 = retorno acumulado CERRADO (%)      -> Delta c2 = resultado realizado
  c3 = P&L ABIERTO en curso (%)
  c5 = tamano / apalancamiento de la posicion (constante en 88% de episodios)
  c8 = OPERACIONES ABIERTAS SIMULTANEAS (1..7), 0 si plano
  c9 = instrumentos con signo; '±X' = largo y corto de X a la vez

Un grid/martingala tiene seis firmas. Ninguna es concluyente por si sola;
juntas son inconfundibles:

  R1  ANADIR A PERDEDORAS   c8 sube mientras c3 cae y es negativo
  R2  ESCALAR EL TAMANO     c5 sube dentro del episodio mientras c3 < 0
  R3  COBERTURA             aparece '±' (largo y corto del mismo activo)
  R4  MUCHAS SIMULTANEAS    c8 maximo alto y frecuente
  R5  ASIMETRIA DEL RESULTADO  muchas ganancias pequenas, pocas perdidas
                               enormes -> asimetria negativa fuerte
  R6  NO CORTAR PERDIDAS    las perdedoras duran mucho mas que las ganadoras
"""
import numpy as np
import pandas as pd

# Umbrales calibrados contra THL como REFERENCIA NEGATIVA medida:
#   R1 ratio 0.59 · R2 0.000 · R3 0.13% · R4 2.8% · R5 +1.01 · R6 1.44
# Se fijan lo bastante cerca de esos valores para que cualquier desviacion
# real dispare, pero no tanto que THL se marque a si mismo.
UMBRALES = dict(R1_p=0.35, R1_ratio=1.5, R2=0.02, R3=0.01,
                R4_frac=0.08, R5=-0.50, R6=2.0)


def cargar(path="journal_decodificado.csv"):
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
    df = df.sort_values("c1").reset_index(drop=True)
    df["c9s"] = df["c9"].astype(str).replace("nan", "")
    df["plano"] = df["c9s"] == ""
    df["ep"] = (df["plano"] != df["plano"].shift()).cumsum()
    return df


def analizar(df, nombre):
    ab = df[~df["plano"]].copy()
    eps = list(ab.groupby("ep"))
    print("=" * 74)
    print("DETECTOR DE GRID/MARTINGALA  ·  %s" % nombre)
    print("=" * 74)
    print("registros %d · con posicion %d · episodios %d"
          % (len(df), len(ab), len(eps)))
    print()

    # ---------------- R1: anadir a perdedoras -----------------------
    sube_perd = sube_gana = tot_perd = tot_gana = 0
    for _, g in eps:
        c3 = pd.to_numeric(g["c3"], errors="coerce").values
        c8 = pd.to_numeric(g["c8"], errors="coerce").values
        for i in range(1, len(g)):
            d8 = c8[i] - c8[i - 1]
            perdiendo = c3[i - 1] < 0 and c3[i] < c3[i - 1]
            ganando = c3[i - 1] > 0 and c3[i] > c3[i - 1]
            if perdiendo:
                tot_perd += 1
                sube_perd += (d8 > 0)
            elif ganando:
                tot_gana += 1
                sube_gana += (d8 > 0)
    p_perd = sube_perd / max(1, tot_perd)
    p_gana = sube_gana / max(1, tot_gana)
    print("R1  ANADIR A PERDEDORAS")
    print("    P(abrir otra | la posicion pierde y empeora) = %.1f%%  (n=%d)"
          % (100 * p_perd, tot_perd))
    print("    P(abrir otra | la posicion gana y mejora)    = %.1f%%  (n=%d)"
          % (100 * p_gana, tot_gana))
    print("    ratio perdedoras/ganadoras = %.2f   [grid: >> 1]"
          % (p_perd / max(1e-9, p_gana)))
    r1 = (p_perd > UMBRALES["R1_p"]
          and p_perd > UMBRALES["R1_ratio"] * p_gana)
    print("    -> %s" % ("SOSPECHOSO" if r1 else "limpio"))
    print()

    # ---------------- R2: escalar el tamano -------------------------
    esc = 0
    con = 0
    for _, g in eps:
        c5 = pd.to_numeric(g["c5"], errors="coerce").values
        c3 = pd.to_numeric(g["c3"], errors="coerce").values
        if len(g) < 2:
            continue
        con += 1
        for i in range(1, len(g)):
            if c5[i] > c5[i - 1] * 1.05 and c3[i - 1] < 0:
                esc += 1
                break
    f_esc = esc / max(1, con)
    print("R2  ESCALAR EL TAMANO EN PERDIDAS")
    print("    episodios en que c5 crece >5%% estando en perdida: %.1f%%  (n=%d)"
          % (100 * f_esc, con))
    r2 = f_esc > UMBRALES["R2"]
    print("    -> %s" % ("SOSPECHOSO" if r2 else "limpio"))
    print()

    # ---------------- R3: cobertura ---------------------------------
    n_hedge = int(df["c9s"].str.contains("±", regex=False).sum())
    print("R3  COBERTURA (largo y corto del mismo activo)")
    print("    registros con '±': %d  (%.2f%% del total)"
          % (n_hedge, 100.0 * n_hedge / len(df)))
    r3 = n_hedge > UMBRALES["R3"] * len(df)
    print("    -> %s" % ("SOSPECHOSO" if r3 else
                         "limpio (residual)" if n_hedge else "limpio"))
    print()

    # ---------------- R4: muchas simultaneas ------------------------
    c8 = pd.to_numeric(ab["c8"], errors="coerce")
    print("R4  OPERACIONES SIMULTANEAS")
    print("    max %d · media %.2f · p95 %.0f"
          % (c8.max(), c8.mean(), c8.quantile(.95)))
    print("    reparto:", "  ".join("%d:%.1f%%" % (k, 100.0 * v / len(c8))
                                    for k, v in
                                    sorted(c8.value_counts().items())))
    # la media no discrimina (THL 1.92 vs grid sintetica 1.96); lo que
    # discrimina es el PESO DE LA COLA: fraccion de registros con >=5 abiertas
    frac5 = float((c8 >= 5).mean())
    print("    fraccion de registros con >=5 abiertas: %.1f%%  [THL: 2.8%%]"
          % (100 * frac5))
    r4 = frac5 > UMBRALES["R4_frac"]
    print("    -> %s" % ("SOSPECHOSO" if r4 else "limpio"))
    print()

    # ---------------- R5: asimetria del resultado -------------------
    res = []
    dur = []
    for _, g in eps:
        c2 = pd.to_numeric(g["c2"], errors="coerce").values
        res.append(c2[-1] - c2[0])
        dur.append((g["c1"].iloc[-1] - g["c1"].iloc[0]) / 60000.0)
    res = np.array(res)
    dur = np.array(dur)
    # asimetria robusta y ratio de colas
    from scipy import stats
    sk = stats.skew(res)
    p01, p99 = np.percentile(res, [1, 99])
    print("R5  ASIMETRIA DEL RESULTADO POR EPISODIO (Delta c2, en %)")
    print("    media %.4f · mediana %.4f · sd %.4f"
          % (res.mean(), np.median(res), res.std()))
    print("    asimetria %.2f   [grid: muy negativa]" % sk)
    print("    p1 %.3f   p99 %.3f   ratio cola izq/der %.2f"
          % (p01, p99, abs(p01) / max(1e-9, abs(p99))))
    print("    %% de episodios positivos: %.1f%%" % (100.0 * (res > 0).mean()))
    r5 = sk < UMBRALES["R5"]
    print("    -> %s" % ("SOSPECHOSO" if r5 else "limpio"))
    print()

    # ---------------- R6: no cortar perdidas ------------------------
    gan = dur[res > 0]
    per = dur[res < 0]
    rat = (np.median(per) / max(1e-9, np.median(gan))) if len(per) and len(gan) else np.nan
    print("R6  DURACION: PERDEDORAS vs GANADORAS (minutos)")
    print("    mediana ganadoras %.1f (n=%d) · mediana perdedoras %.1f (n=%d)"
          % (np.median(gan) if len(gan) else -1, len(gan),
             np.median(per) if len(per) else -1, len(per)))
    print("    ratio %.2f   [grid: >> 1, nunca corta]" % rat)
    r6 = rat > UMBRALES["R6"]
    print("    -> %s" % ("SOSPECHOSO" if r6 else "limpio"))
    print()

    # ---------------- veredicto -------------------------------------
    banderas = dict(R1=r1, R2=r2, R3=r3, R4=r4, R5=r5, R6=r6)
    n = sum(banderas.values())
    print("-" * 74)
    print("BANDERAS: %s" % ("  ".join("%s=%s" % (k, "SI" if v else "no")
                                      for k, v in banderas.items())))
    print("TOTAL: %d de 6" % n)
    if n == 0:
        v = "LIMPIO — sin rasgos de grid ni martingala"
    elif n <= 1:
        v = "PROBABLEMENTE LIMPIO — una sola bandera, revisar a mano"
    elif n <= 3:
        v = "DUDOSO — no asignar capital sin entender el mecanismo"
    else:
        v = "RECHAZAR — perfil de grid/martingala"
    print("VEREDICTO: %s" % v)
    print("-" * 74)
    return dict(nombre=nombre, banderas=banderas, n=n, res=res, dur=dur)


if __name__ == "__main__":
    df = cargar()
    analizar(df, "THL (D.259985) — joxemi")
