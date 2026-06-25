# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

import re

from controlcomparador.config import (
    PATRON_CARRERA_PDF,
    PATRON_APUESTA_VALOR,
    PATRON_EXCLUIR_PASE_SIN_FINAL,
    PATRON_FINAL,
    PATRON_PRIMER_PASE,
    PATRON_PASE_TELA,
    PATRON_LINEA_APUESTA,
    PATRON_CABALLO,
    PATRON_FECHA,
    PATRON_FILA_PALERMO,
    PATRON_APUESTAS_A,
    PATRON_CARRERA_OFICIAL,
    MAPEO_ABREVIATURAS,
    CODIGOS_APUESTA_VALIDOS,
    APUESTAS_SIN_COMPARAR_VALOR,
)
from controlcomparador.utils.money import parsear_monto_str


def es_apuesta_excluida(nombre: str) -> bool:
    if not nombre:
        return False
    if nombre.strip().lower().startswith("doble"):
        return False
    if PATRON_EXCLUIR_PASE_SIN_FINAL.search(nombre):
        return True
    if PATRON_FINAL.search(nombre):
        if PATRON_PRIMER_PASE.search(nombre):
            return False
        return True
    return False


def normalizar_nombre_apuesta(nombre: str) -> str:
    nombre = nombre.strip()
    if not nombre:
        return nombre
    palabras = nombre.split()
    if not palabras:
        return nombre
    primera_palabra = palabras[0]
    if "pase" in nombre.lower() or primera_palabra.lower() in MAPEO_ABREVIATURAS:
        return primera_palabra
    return nombre


def abreviar_apuesta(nombre: str) -> str:
    nombre = (nombre or "").strip()
    if not nombre:
        return nombre
    return MAPEO_ABREVIATURAS.get(nombre.lower(), nombre)


def obtener_carreras_por_pagina(ruta_pdf: str | Path) -> list[dict]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []
    for num_pagina in range(len(reader.pages)):
        pagina_actual = num_pagina + 1
        texto = reader.pages[num_pagina].extract_text() or ""
        numero_carrera = None
        nombre_carrera = None
        m = PATRON_CARRERA_PDF.search(texto)
        if m:
            numero_carrera = int(m.group(1))
            nombre_carrera = m.group(2).strip()
            nombre_carrera = " ".join(nombre_carrera.split())
        resultado.append({
            "pagina": pagina_actual,
            "numero_carrera": numero_carrera,
            "nombre_carrera": nombre_carrera,
        })
    return resultado


def obtener_caballos_por_carrera(ruta_pdf: str | Path) -> dict[int, int]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado: dict[int, int] = {}
    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        m_carrera = PATRON_CARRERA_PDF.search(texto)
        if not m_carrera:
            continue
        num_carrera = int(m_carrera.group(1))
        numeros_caballos = set()
        for m in PATRON_CABALLO.finditer(texto):
            num = int(m.group(1))
            if 1 <= num <= 24:
                numeros_caballos.add(num)
        cantidad = max(numeros_caballos) if numeros_caballos else 0
        resultado[num_carrera] = cantidad
    return resultado


def _obtener_apuestas_programa_oficial(ruta_pdf: str | Path) -> list[list]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []
    caballos_por_carrera = obtener_caballos_por_carrera(ruta_pdf)
    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        m_carrera = PATRON_CARRERA_PDF.search(texto)
        if not m_carrera:
            continue
        num_carrera = int(m_carrera.group(1))
        cantidad_caballos = caballos_por_carrera.get(num_carrera, 0)
        lineas = texto.split("\n")
        bloque_apuestas = []
        for i, lin in enumerate(lineas):
            if "APUESTAS:" in lin.upper():
                idx = lin.upper().index("APUESTAS:")
                linea_inicial = lin[idx + len("APUESTAS:"):].strip()
                if linea_inicial:
                    bloque_apuestas.append(linea_inicial)
                max_lineas_continuacion = 6
                j = i + 1
                while j < len(lineas) and len(bloque_apuestas) < (1 + max_lineas_continuacion):
                    sig = lineas[j].strip()
                    if not sig:
                        break
                    if not PATRON_LINEA_APUESTA.search(sig):
                        break
                    bloque_apuestas.append(sig)
                    j += 1
                break
        texto_apuestas = " ".join(bloque_apuestas)
        if not texto_apuestas:
            continue
        for m in PATRON_APUESTA_VALOR.finditer(texto_apuestas):
            apuesta_bruta = m.group(1).strip().rstrip(",")
            valor = m.group(2).strip()
            if not apuesta_bruta or not valor:
                continue
            if "Ganador" in apuesta_bruta:
                partes = [p.strip() for p in apuesta_bruta.split(",") if p.strip()]
                for p in partes:
                    p_norm = normalizar_nombre_apuesta(p)
                    p_cod = abreviar_apuesta(p_norm)
                    if p_cod in CODIGOS_APUESTA_VALIDOS:
                        resultado.append([num_carrera, cantidad_caballos, p_cod, ""])
                continue
            apuesta = apuesta_bruta
            if "," in apuesta:
                apuesta = apuesta.rsplit(",", 1)[-1].strip()
            if not es_apuesta_excluida(apuesta):
                apuesta_normalizada = normalizar_nombre_apuesta(apuesta)
                apuesta_cod = abreviar_apuesta(apuesta_normalizada)
                if apuesta_cod in CODIGOS_APUESTA_VALIDOS:
                    resultado.append([num_carrera, cantidad_caballos, apuesta_cod, valor])
    return resultado


# --- Tela Oficial San Isidro PDF ---

PATRON_BET_VALUE = re.compile(r"(.+?)\s*\$\s*([\d.,]+)")
PATRON_EXTRA_BETS = re.compile(
    r"(Cuaterna|Triplo|Quintuplo|Cadena|Doble|Imperfecta|Cuatrifecta)", re.IGNORECASE
)
PATRON_CABALLO_TELA = re.compile(r"\s+(\d+)\s{2,}(?:[A-Z]|')")


def es_tela_oficial(ruta_pdf: str | Path) -> bool:
    """Detecta si un PDF es de formato 'Tela Oficial' (Programa Depurado)."""
    import pypdf
    try:
        reader = pypdf.PdfReader(ruta_pdf)
        if not reader.pages:
            return False
        texto = (reader.pages[0].extract_text() or "")
        return "Programa Depurado" in texto
    except Exception:
        return False


def _parsear_bets_tela(texto: str) -> list[tuple[str, str]]:
    """Parsea linea de apuestas formato tela: 'Nombre1 $ Valor, Nombre2 $ Valor'.
    Retorna [(codigo, valor_str), ...]."""
    resultado: list[tuple[str, str]] = []
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    for p in partes:
        m_val = re.search(r"\$\s*([\d.,]+)", p)
        if m_val:
            nombre = re.sub(r"\$\s*[\d.,]+", "", p).strip().rstrip(",")
            valor = m_val.group(1)
        else:
            nombre = p
            valor = ""
        if not nombre:
            continue
        if es_apuesta_excluida(nombre):
            continue
        codigo = abreviar_apuesta(normalizar_nombre_apuesta(nombre))
        if codigo and codigo in CODIGOS_APUESTA_VALIDOS:
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                resultado.append((codigo, ""))
            else:
                resultado.append((codigo, valor))
    return resultado


def _obtener_apuestas_tela_oficial(ruta_pdf: str | Path) -> list[list]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado: list[list] = []

    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        lineas = texto.split("\n")
        if not lineas:
            continue

        # Find APUESTAS lines (each marks a unique race)
        apuestas_indices = [
            i for i, l in enumerate(lineas)
            if l.strip().upper().startswith("APUESTAS:")
        ]
        if not apuestas_indices:
            continue

        for idx, start_idx in enumerate(apuestas_indices):
            end_idx = apuestas_indices[idx + 1] if idx + 1 < len(apuestas_indices) else len(lineas)
            race_lines = lineas[start_idx:end_idx]

            # --- APUESTAS base ---
            texto_apuestas = ""
            for l in race_lines:
                s = l.strip()
                if s.upper().startswith("APUESTAS:"):
                    texto_apuestas = s[len("APUESTAS:"):].strip()
                    break

            # --- Extra bets (despues de Bolsa Total, antes del nro de carrera) ---
            extra_bets: list[str] = []
            found_bolsa = False
            for l in race_lines:
                s = l.strip()
                if "Bolsa Total:" in s:
                    found_bolsa = True
                    continue
                if found_bolsa:
                    if s.isdigit() and 1 <= int(s) <= 30:
                        break
                    if "CHAQUETILLAS" in s:
                        break
                    if PATRON_EXTRA_BETS.search(s) and "$" in s:
                        if s not in extra_bets:
                            extra_bets.append(s)

            # --- Nro de carrera (buscar ANTES del marcador APUESTAS:) ---
            num_carrera = None
            for back in range(start_idx - 1, max(start_idx - 15, -1), -1):
                s = lineas[back].strip()
                if s.isdigit() and 1 <= int(s) <= 30:
                    num_carrera = int(s)
                    break
            if num_carrera is None:
                for l in race_lines:
                    s = l.strip()
                    if s.isdigit() and 1 <= int(s) <= 30:
                        num_carrera = int(s)
                        break
            if num_carrera is None:
                continue

            # --- Caballos ---
            horse_nums: set[int] = set()
            in_horse_block = False
            for l in race_lines:
                s = l.strip()
                if "CHAQUETILLAS" in s:
                    in_horse_block = False
                    continue
                if re.search(r"\bCABALLO\b", s, re.IGNORECASE) and "JOCKEY" in s.upper():
                    in_horse_block = True
                    continue
                if in_horse_block:
                    if not s or s.startswith("Bolsa") or s.startswith("Total") or s.startswith("*"):
                        continue
                    if s.isdigit():
                        continue
                    if re.match(r"\d{1,2}:\d{2}", s):
                        continue
                    m = PATRON_CABALLO_TELA.search(s)
                    if m:
                        num = int(m.group(1))
                        if 1 <= num <= 30:
                            horse_nums.add(num)

            num_caballos = len(horse_nums) if horse_nums else 0

            # --- Combinar todas las apuestas ---
            apuestas_vistas: set[str] = set()

            if texto_apuestas:
                for cod, val in _parsear_bets_tela(texto_apuestas):
                    if cod not in apuestas_vistas:
                        resultado.append([num_carrera, num_caballos, cod, val])
                        apuestas_vistas.add(cod)

            for eb in extra_bets:
                for cod, val in _parsear_bets_tela(eb):
                    if cod not in apuestas_vistas:
                        resultado.append([num_carrera, num_caballos, cod, val])
                        apuestas_vistas.add(cod)

    return resultado


def extraer_info_reunion_tela(ruta_pdf: str | Path) -> dict[str, str]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    texto = (reader.pages[0].extract_text() or "").split("\n")
    reunion = ""
    fecha = ""
    hipodromo = ""
    for line in texto:
        s = line.strip()
        m = re.search(r"Reunion\s+(\d+)", s, re.IGNORECASE)
        if m:
            reunion = m.group(1)
        d = re.search(r"(\d{2}/\d{2}/\d{4})", s)
        if d:
            fecha = d.group(1)
        if "Hipodromo" in s:
            hipodromo = s
    return {"reunion": reunion, "fecha": fecha, "hipodromo": hipodromo}


def obtener_apuestas_por_carrera(ruta_pdf: str | Path) -> list[list]:
    """Auto-detecta el formato del PDF y extrae las apuestas."""
    if es_tela_oficial(ruta_pdf):
        return _obtener_apuestas_tela_oficial(ruta_pdf)
    return _obtener_apuestas_programa_oficial(ruta_pdf)


def extraer_pases_tela_oficial(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    """Extrae info de pases (1er.Pase, 2do.Pase, etc.) para apuestas pick.
    Retorna {num_carrera: {codigo: {pase_normalizado, ...}}}"""
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado: dict[int, dict[str, set[str]]] = {}

    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        lineas = texto.split("\n")
        if not lineas:
            continue

        apuestas_indices = [
            i for i, l in enumerate(lineas)
            if l.strip().upper().startswith("APUESTAS:")
        ]
        if not apuestas_indices:
            continue

        for idx, start_idx in enumerate(apuestas_indices):
            end_idx = apuestas_indices[idx + 1] if idx + 1 < len(apuestas_indices) else len(lineas)
            race_lines = lineas[start_idx:end_idx]

            # Extraer nro de carrera (buscar ANTES del marcador APUESTAS:)
            num_carrera = None
            for back in range(start_idx - 1, max(start_idx - 15, -1), -1):
                s = lineas[back].strip()
                if s.isdigit() and 1 <= int(s) <= 30:
                    num_carrera = int(s)
                    break
            if num_carrera is None:
                for l in race_lines:
                    s = l.strip()
                    if s.isdigit() and 1 <= int(s) <= 30:
                        num_carrera = int(s)
                        break
            if num_carrera is None:
                continue

            pases_carrera: dict[str, set[str]] = {}

            for l in race_lines:
                s = l.strip()
                if not s:
                    continue
                if s == "CHAQUETILLAS":
                    continue
                for m in PATRON_PASE_TELA.finditer(s):
                    bet_raw = m.group(1).lower()
                    pase_raw = m.group(2)
                    pase_norm = _normalizar_pase(pase_raw)
                    codigo = abreviar_apuesta(bet_raw)
                    if codigo:
                        pases_carrera.setdefault(codigo, set()).add(pase_norm)

            if pases_carrera:
                resultado[num_carrera] = pases_carrera

    return resultado


def _normalizar_pase(pase: str) -> str:
    """Normaliza nombre de pase a formato consistente.
    1er. Pase  -> 1er.Pase
    ultimo pase -> Ultimo Pase
    1er.Pase   -> 1er.Pase
    2do .pase  -> 2do.Pase
    2do.pa se  -> 2do.Pase"""
    pase = pase.strip().lower()
    pase = re.sub(r"p\s*a\s*s\s*e", "pase", pase)
    pase = re.sub(r"\s+", " ", pase)
    pase = re.sub(r"\s+(\.)", r"\1", pase)
    pase = re.sub(r"(\.)\s+", r"\1", pase)
    pase = re.sub(r"\bpase\b", "Pase", pase)
    if pase:
        pase = pase[0].upper() + pase[1:]
    return pase


def normalizar_desde_lista_apuestas(apuestas_raw: list[list]) -> dict[int, dict]:
    resultado: dict[int, dict] = {}
    for num_carrera, cantidad_caballos, codigo_apuesta, valor_str in apuestas_raw:
        if num_carrera not in resultado:
            resultado[num_carrera] = {"caballos": cantidad_caballos, "apuestas": {}}
        valor_float = parsear_monto_str(valor_str)
        resultado[num_carrera]["apuestas"][codigo_apuesta] = valor_float
    return resultado


def normalizar_pdf(ruta_pdf: str | Path, apuestas_raw: Optional[list[list]] = None) -> dict[int, dict]:
    if apuestas_raw is None:
        apuestas_raw = obtener_apuestas_por_carrera(ruta_pdf)
    return normalizar_desde_lista_apuestas(apuestas_raw)


# --- Palermo PDF ---

def _mapear_nombre_apuesta_palermo(descripcion: str) -> Optional[str]:
    if not descripcion:
        return None
    texto = descripcion.strip().lower()
    texto = texto.replace("  ", " ")
    if "cuatrifecta" in texto:
        return "CUA"
    if "trifecta" in texto:
        return "TRI"
    if "doble extra" in texto:
        return "DOB"
    if "doble" in texto:
        return "DOB"
    if "5 y 6" in texto or "5y6" in texto or "5 & 6" in texto:
        return "CAD"
    if "pick cuatro" in texto or "pick 4" in texto:
        return "QTN"
    if "pick cinco" in texto or "pick 5" in texto:
        return "QTP"
    if "exacta" in texto:
        return "EXA"
    if "triplo" in texto:
        return "TPL"
    if "imperfecta" in texto:
        return "IMP"
    return None


def _extraer_carreras_palermo(carreras_str: str) -> list[int]:
    texto = carreras_str.upper()
    m_rango = re.search(r"DESDE\s+LA\s+(\d+)\s*[ªº]?\s+HASTA\s+LA\s+(\d+)\s*[ªº]?", texto)
    if m_rango:
        inicio = int(m_rango.group(1))
        fin = int(m_rango.group(2))
        if inicio <= fin:
            return list(range(inicio, fin + 1))
    numeros = re.findall(r"(\d+)\s*[ªº]?", carreras_str)
    return [int(n) for n in numeros]


def leer_palermo_desde_pdf(ruta_pdf: str | Path) -> dict:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    fechas_encontradas: list[str] = []
    apuestas_por_fecha: dict[str, dict[int, dict[str, Optional[float]]]] = {}
    resumen_por_fecha: dict[str, dict[str, dict]] = {}

    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        fecha_actual: Optional[str] = None
        for linea in texto.split("\n"):
            linea_stripped = linea.strip()
            if not linea_stripped:
                continue
            for f in PATRON_FECHA.findall(linea_stripped):
                if f not in fechas_encontradas:
                    fechas_encontradas.append(f)
                fecha_actual = f
            if "(" not in linea_stripped or ")" not in linea_stripped:
                continue
            m = PATRON_FILA_PALERMO.match(linea_stripped)
            if not m:
                continue
            if not fecha_actual:
                continue
            descripcion = m.group(1).strip()
            monto_str = m.group(2).strip()
            carreras_str = m.group(3).strip()
            codigo_apuesta = _mapear_nombre_apuesta_palermo(descripcion)
            if not codigo_apuesta:
                continue
            valor = parsear_monto_str(monto_str)
            if valor is None:
                continue
            carreras = _extraer_carreras_palermo(carreras_str)
            if not carreras:
                continue
            if fecha_actual not in apuestas_por_fecha:
                apuestas_por_fecha[fecha_actual] = {}
            if fecha_actual not in resumen_por_fecha:
                resumen_por_fecha[fecha_actual] = {}
            if codigo_apuesta not in resumen_por_fecha[fecha_actual]:
                resumen_por_fecha[fecha_actual][codigo_apuesta] = {
                    "conteo_lineas": 0,
                    "valor": valor,
                    "carreras": set(),
                }
            resumen_por_fecha[fecha_actual][codigo_apuesta]["conteo_lineas"] += 1
            resumen_por_fecha[fecha_actual][codigo_apuesta]["valor"] = valor
            for carrera in carreras:
                if carrera not in apuestas_por_fecha[fecha_actual]:
                    apuestas_por_fecha[fecha_actual][carrera] = {}
                apuestas_por_fecha[fecha_actual][carrera][codigo_apuesta] = valor
                if isinstance(resumen_por_fecha[fecha_actual][codigo_apuesta]["carreras"], set):
                    resumen_por_fecha[fecha_actual][codigo_apuesta]["carreras"].add(carrera)

    return {
        "fechas": fechas_encontradas,
        "apuestas_por_fecha": apuestas_por_fecha,
        "resumen_por_fecha": resumen_por_fecha,
    }


# --- Oficial Palermo PDF ---

def _mapear_apuesta_oficial(nombre: str) -> Optional[str]:
    n = (nombre or "").strip().lower()
    if not n:
        return None
    n = n.split("$", 1)[0].strip()
    if n in {"ganador", "segundo", "tercero"}:
        return None
    n = " ".join(n.split())
    if "doble extra" in n or n == "doble":
        return "DOB"
    if n in {"5 y 6", "5y6", "5 & 6"}:
        return "CAD"
    if n in {"pick 4", "pick cuatro"}:
        return "QTN"
    if n == "triplo":
        return "TPL"
    if n == "exacta":
        return "EXA"
    if n == "trifecta":
        return "TRI"
    if n == "imperfecta":
        return "IMP"
    if n == "cuatrifecta":
        return "CUA"
    return None


def extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial: str | Path) -> list[dict]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf_oficial)
    carreras_apuestas: dict[int, set[str]] = {}
    ultima_carrera_detectada: Optional[int] = None

    for page in reader.pages:
        texto = page.extract_text() or ""
        if not texto.strip():
            continue
        lineas = texto.split("\n")
        carreras_en_pagina: list[tuple[int, int]] = []
        apuestas_en_pagina: list[tuple[int, str]] = []

        for idx, linea in enumerate(lineas):
            l = (linea or "").strip()
            if not l:
                continue
            mc = PATRON_CARRERA_OFICIAL.search(l)
            if mc:
                carreras_en_pagina.append((idx, int(mc.group(1))))
            ma = PATRON_APUESTAS_A.search(l)
            if ma:
                apuestas_en_pagina.append((idx, ma.group(1)))

        if not apuestas_en_pagina:
            continue
        if not carreras_en_pagina and ultima_carrera_detectada is not None:
            carreras_en_pagina = [(0, ultima_carrera_detectada + 1)]
        if not carreras_en_pagina:
            continue
        ultima_carrera_detectada = max(n for _, n in carreras_en_pagina)

        for idx_apuesta, listado in apuestas_en_pagina:
            previas = [(i, n) for (i, n) in carreras_en_pagina if i <= idx_apuesta]
            if previas:
                num_carrera = previas[-1][1]
            else:
                num_carrera = carreras_en_pagina[0][1]
            if num_carrera not in carreras_apuestas:
                carreras_apuestas[num_carrera] = set()
            partes = [p.strip() for p in listado.split(",") if p.strip()]
            for p in partes:
                cod = _mapear_apuesta_oficial(p)
                if cod:
                    carreras_apuestas[num_carrera].add(cod)

    resultado = []
    for num_carrera in sorted(carreras_apuestas.keys()):
        resultado.append({
            "carrera": num_carrera,
            "apuestas": sorted(carreras_apuestas[num_carrera]),
        })
    return resultado
