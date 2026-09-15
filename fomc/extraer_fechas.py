#!/usr/bin/env python3
"""
Extrae las fechas de ANUNCIO del FOMC, 2000-2026, de las paginas de la Fed.

Version 2. La v1 perdia todas las reuniones A CABALLO DE DOS MESES, porque el
formato real es 'Jan/Feb 31-1 Meeting' o 'April/May 30-1 Meeting' y mi regex
exigia un nombre de mes completo seguido de digitos.

Dos metodos independientes, cruzados:

  METODO A (texto): etiquetas explicitas del tipo
        'January 26-27 Meeting'     -> anuncio el 27 de enero
        'Jan/Feb 31-1 Meeting'      -> anuncio el 1 de febrero
        'March 16 Meeting'          -> anuncio el 16 de marzo
     Se excluye todo lo que sea 'Conference Call' o 'notation vote': el efecto
     de Lucca y Moench es solo para reuniones PROGRAMADAS.

  METODO B (URLs): los nombres de fichero llevan la fecha exacta del anuncio
        /fomc/minutes/20000202.htm · fomcminutes20100127.htm
        press/monetary/2005/20050202 · monetary20150128a1.pdf

El metodo A dice CUALES cuentan; el B confirma la fecha exacta.
"""
import os
import re
import html
import datetime as dt
import pandas as pd

DIR = "paginas"
MES = {}
for i, nom in enumerate(["January", "February", "March", "April", "May",
                         "June", "July", "August", "September", "October",
                         "November", "December"]):
    MES[nom.lower()] = i + 1
    MES[nom[:3].lower()] = i + 1
MES["sept"] = 9

NOMBRES = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)[a-z]*"


def plano(path):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def metodo_a(anio, path):
    """Devuelve el conjunto de fechas de anuncio de reuniones PROGRAMADAS."""
    if not os.path.exists(path):
        return set()
    txt = plano(path)
    if anio >= 2021:                      # aislar el bloque del año
        partes = re.split(r"(\d{4}) FOMC Meetings", txt)
        txt = ""
        for i in range(1, len(partes) - 1, 2):
            if int(partes[i]) == anio:
                txt = partes[i + 1]
                break
        if not txt:
            return set()

    out = set()
    # 'Mes[/Mes2] dias (Meeting|Conference Call|notation vote)'
    pat = (r"(%s)(?:\s*/\s*(%s))?\s+([0-9]{1,2}(?:\s*[-/]\s*[0-9]{1,2})?)\s*"
           r"(?:\(([^)]*)\)\s*)?(Meeting|Conference Call|notation vote)"
           % (NOMBRES, NOMBRES))
    for m1, m2, dias, paren, tipo in re.findall(pat, txt, flags=re.I):
        if tipo.lower() != "meeting":
            continue
        if paren and "notation" in paren.lower():
            continue
        nums = re.findall(r"\d+", dias)
        d = int(nums[-1])
        mes_txt = (m2 or m1).lower()
        mm = MES.get(mes_txt[:4]) or MES.get(mes_txt[:3])
        if mm is None:
            continue
        # si cruza de diciembre a enero el año avanza
        yy = anio + 1 if (m2 and MES.get(m1.lower()[:3]) == 12 and mm == 1) \
            else anio
        try:
            out.add(dt.date(yy, mm, d))
        except ValueError:
            pass
    return out


PATRONES_URL = [
    r"/fomc/minutes/(\d{8})", r"fomcminutes(\d{8})",
    r"press/monetary/\d{4}/(\d{8})", r"press/general/\d{4}/(\d{8})",
    r"monetary(\d{8})a", r"FOMC(\d{8})Agenda", r"fomc(\d{8})gbpt",
]


def metodo_b(anio, path):
    if not os.path.exists(path):
        return set()
    t = open(path, encoding="utf-8", errors="ignore").read()
    out = set()
    for pat in PATRONES_URL:
        for s in re.findall(pat, t, flags=re.I):
            try:
                d = dt.datetime.strptime(s, "%Y%m%d").date()
            except ValueError:
                continue
            if d.year == anio:
                out.add(d)
    return out


print("=" * 80)
print("FECHAS DE ANUNCIO DEL FOMC · metodo A (cuales) x metodo B (fecha exacta)")
print("=" * 80)
print(f"{'año':>6}{'A':>5}{'B':>5}{'A∩B':>6}{'usadas':>8}   nota")
print("-" * 80)

filas, avisos = [], []
for anio in range(2000, 2027):
    path = os.path.join(DIR, "hist%d.html" % anio) if anio <= 2020 \
        else os.path.join(DIR, "calendario.html")
    A = metodo_a(anio, path)
    B = metodo_b(anio, path) if anio <= 2020 else set()
    if anio > 2020:
        cal = metodo_b(anio, os.path.join(DIR, "calendario.html"))
        B = {d for d in cal if d.year == anio}
    inter = A & B
    # A manda sobre cuales cuentan; B confirma
    usar = A if A else B
    nota = ""
    if A and B:
        solo_a = A - B
        if solo_a:
            nota = "en A y no en B: %s" % ", ".join(str(x) for x in
                                                   sorted(solo_a))
            avisos.append((anio, nota))
    if not A:
        nota = "sin etiquetas de texto, se usa B"
    print(f"{anio:>6}{len(A):>5}{len(B):>5}{len(inter):>6}{len(usar):>8}   {nota}")
    for d in sorted(usar):
        filas.append(d)

df = pd.DataFrame({"fecha": sorted(set(filas))})
df["anio"] = pd.to_datetime(df["fecha"]).dt.year
df["conf_prensa"] = df["fecha"] >= dt.date(2011, 4, 27)

print()
print("=" * 80)
print("VALIDACION")
print("=" * 80)
print("total: %d anuncios · %s -> %s"
      % (len(df), df["fecha"].min(), df["fecha"].max()))
print()
malos = []
for y, n in df.groupby("anio").size().items():
    esperado = 8
    ok = (n == esperado) or (y == 2026)
    print("   %d: %-9s %s" % (y, "#" * n, "" if ok else "<-- %d" % n))
    if not ok:
        malos.append(y)
if malos:
    print()
    print("Años que no dan 8 — se listan para revision manual:")
    for y in malos:
        print("   %d: %s" % (y, ", ".join(
            str(x) for x in df[df["anio"] == y]["fecha"])))
else:
    print()
    print("Todos los años completos dan 8 reuniones programadas.")

if avisos:
    print()
    print("Discrepancias A vs B (fecha en texto sin URL que la confirme):")
    for y, n in avisos:
        print("   %d: %s" % (y, n))

df[["fecha", "conf_prensa"]].to_csv("fomc_fechas.csv", index=False)
print()
print("Guardado fomc_fechas.csv (%d filas)" % len(df))
