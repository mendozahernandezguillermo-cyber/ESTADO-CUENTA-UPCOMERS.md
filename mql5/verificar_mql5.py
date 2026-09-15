#!/usr/bin/env python3
"""
COMPROBADOR ESTATICO PARA LOS EA.

Existe porque tres veces seguidas un parche mio no encontro su ancla y se
aplico A MEDIAS: quedaron usos de variables que nunca se declararon y una
funcion definida dos veces. El balance de llaves y parentesis, que era lo
unico que comprobaba, daba OK en los tres casos.

Comprueba cuatro cosas, todas mecanicas:
  1. balance de llaves, parentesis y corchetes
  2. FUNCIONES DEFINIDAS DOS VECES  (el error 'already defined and has body')
  3. IDENTIFICADORES USADOS Y NUNCA DECLARADOS  (el 'undeclared identifier')
  4. declaraciones adelantadas sin definicion

Uso:  python3 verificar_mql5.py [fichero.mq5 ...]
"""
import re
import sys
import io

# nombres de TIPO: aparecen como identificadores en declaraciones y en casts
TIPOS_NOMBRES = {
    "void", "bool", "char", "uchar", "short", "ushort", "int", "uint",
    "long", "ulong", "float", "double", "string", "datetime", "color",
    "MqlTick", "MqlDateTime", "MqlTradeRequest", "MqlTradeResult", "MqlRates",
}

# identificadores de MQL5 que se usan sin declarar en el fichero
PREDEFINIDOS = {
    "_Symbol", "_Point", "_Digits", "_LastError", "_Period",
    "INIT_SUCCEEDED", "INIT_FAILED", "NULL", "true", "false",
    "WHOLE_ARRAY", "EMPTY_VALUE", "INVALID_HANDLE", "CHARTS_MAX",
}

TIPOS = (r"(?:const\s+)?(?:void|bool|char|uchar|short|ushort|int|uint|long|"
         r"ulong|float|double|string|datetime|color|MqlTick|MqlDateTime|"
         r"MqlTradeRequest|MqlTradeResult|MqlRates|ENUM_\w+)")


def sin_comentarios_ni_cadenas(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
    s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
    return s


def cuerpos_de_funcion(t):
    """Devuelve [(nombre, inicio, fin, texto_cuerpo, firma)]."""
    res = []
    patron = re.compile(r"\n" + TIPOS + r"\s+(\w+)\s*\(([^;{)]*)\)\s*\n?\s*\{")
    for m in patron.finditer(t):
        nombre = m.group(1)
        firma = m.group(2)
        i = t.index("{", m.end() - 1)
        nivel, j = 0, i
        while j < len(t):
            if t[j] == "{":
                nivel += 1
            elif t[j] == "}":
                nivel -= 1
                if nivel == 0:
                    break
            j += 1
        res.append((nombre, m.start(), j, t[i:j + 1], firma))
    return res


def revisar(path):
    bruto = io.open(path, encoding="utf-8").read()
    t = sin_comentarios_ni_cadenas(bruto)
    problemas = []

    # ---- 1. balance
    for a, b, nom in (("{", "}", "llaves"), ("(", ")", "parentesis"),
                      ("[", "]", "corchetes")):
        if t.count(a) != t.count(b):
            problemas.append(f"DESCUADRE de {nom}: {t.count(a)} / {t.count(b)}")

    funcs = cuerpos_de_funcion(t)

    # ---- 2. funciones definidas dos veces
    vistos = {}
    for nombre, ini, fin, cuerpo, firma in funcs:
        vistos.setdefault(nombre, []).append(bruto[:ini].count("\n") + 2)
    for nombre, lineas in vistos.items():
        if len(lineas) > 1:
            problemas.append(
                f"FUNCION DEFINIDA {len(lineas)} VECES: '{nombre}' "
                f"en las lineas {lineas}")

    # ---- nombres declarados en ambito global
    globales = set(PREDEFINIDOS)
    globales |= set(re.findall(r"#define\s+(\w+)", bruto))
    globales |= set(re.findall(r"\ninput\s+(?:group\s+)?" + TIPOS + r"\s+(\w+)",
                               t))
    globales |= set(vistos.keys())
    # variables y arrays globales
    cabeza = t
    for nombre, ini, fin, cuerpo, firma in funcs:
        cabeza = cabeza.replace(cuerpo, "")
    globales |= set(re.findall(r"\n\s*" + TIPOS + r"\s+(\w+)\s*(?:\[[^\]]*\])?"
                               r"\s*(?:=|;|,)", cabeza))
    globales |= set(re.findall(r"\n\s*" + TIPOS + r"\s+(\w+)", cabeza))

    # ---- 3. identificadores usados y nunca declarados
    for nombre, ini, fin, cuerpo, firma in funcs:
        linea0 = bruto[:ini].count("\n") + 2
        locales = set(re.findall(r"\b" + TIPOS + r"\s+&?(\w+)", firma))
        locales |= set(re.findall(r"(\w+)\s*\[", cuerpo))   # arrays locales
        #  declaraciones locales, incluidas las de varios nombres por linea
        #  ("double a, b;" o "int i = 0, n = 8;")
        for m2 in re.finditer(r"\b" + TIPOS + r"\s+([^;{}]+);", cuerpo):
            trozo, prof, actual = m2.group(1), 0, ""
            for ch in trozo + ",":
                if ch == "(":
                    prof += 1
                elif ch == ")":
                    prof -= 1
                if ch == "," and prof == 0:
                    mm = re.match(r"\s*&?(\w+)", actual)
                    if mm:
                        locales.add(mm.group(1))
                    actual = ""
                else:
                    actual += ch
        for m in re.finditer(r"\b([A-Za-z_]\w*)\b(\s*)", cuerpo):
            ident = m.group(1)
            if cuerpo[m.end():m.end() + 1] == "(":
                continue                       # llamada a funcion o cast
            if m.start() > 0 and cuerpo[m.start() - 1] == ".":
                continue                       # miembro de estructura
            if ident in TIPOS_NOMBRES:
                continue                       # nombre de tipo
            if ident in locales or ident in globales:
                continue
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", ident):
                continue                       # constante o enum de MQL5
            if re.match(r"^(?:Math|Array|String|Time|Symbol|Account|Position|"
                        r"Order|History|Deal|Global|Chart|File|Print|Copy|"
                        r"Series|Event|Zero|Struct|Normalize|Integer|Double|"
                        r"Terminal|Comment|Alert|Sleep|Bars|iTime|return|if|"
                        r"else|for|while|do|switch|case|break|continue|new|"
                        r"delete|sizeof|static|const)", ident):
                continue
            if ident in ("i", "j", "k", "n", "d"):
                continue
            problemas.append(
                f"IDENTIFICADOR NO DECLARADO: '{ident}' dentro de "
                f"'{nombre}()' (funcion en la linea ~{linea0})")

    # ---- 4. declaradas y no definidas
    dec = set(re.findall(r"\n\s*" + TIPOS + r"\s+(\w+)\s*\([^;{]*\)\s*;", t))
    faltan = dec - set(vistos.keys())
    for f in sorted(faltan):
        problemas.append(f"DECLARADA Y NO DEFINIDA: '{f}()'")

    return problemas, len(bruto.split("\n")), len(funcs)


ficheros = sys.argv[1:] or ["EA_FOMC_Gap.mq5", "EA_Guardian.mq5",
                            "EA_Trend_Multi.mq5"]
total = 0
for f in ficheros:
    try:
        probs, lineas, nf = revisar(f)
    except FileNotFoundError:
        print(f"{f}: no existe")
        continue
    # los problemas se deduplican manteniendo el orden
    vistos_p, unicos = set(), []
    for p in probs:
        if p not in vistos_p:
            vistos_p.add(p)
            unicos.append(p)
    estado = "LIMPIO" if not unicos else f"{len(unicos)} PROBLEMAS"
    print(f"\n{f}  ({lineas} lineas, {nf} funciones)  ->  {estado}")
    for p in unicos:
        print(f"    · {p}")
    total += len(unicos)

print(f"\n{'=' * 60}")
print("TOTAL:", "todo limpio" if total == 0 else f"{total} problemas")
sys.exit(1 if total else 0)
