# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

import re

from controlcomparador.config import (
    PATRON_EXCLUIR_PASE_SIN_FINAL,
    PATRON_FINAL,
    PATRON_PRIMER_PASE,
    PATRON_PASE_TELA,
    PATRON_ULTIMO_PASE,
    PATRON_FECHA,
    PATRON_FILA_PALERMO,
    PATRON_APUESTAS_A,
    PATRON_CARRERA_OFICIAL,
    PATRON_CARRERA_TELA_REPORTE,
    PATRON_PROGRAMA_OFICIAL_REPORTE,
    PATRON_REUNION_TELA_REPORTE,
    MAPEO_ABREVIATURAS,
    CODIGOS_APUESTA_VALIDOS,
    APUESTAS_SIN_COMPARAR_VALOR,
)
from controlcomparador.utils.money import parsear_monto_str


def es_apuesta_excluida(nombre: str) -> bool:
    if not nombre:
        return False
    low = nombre.strip().lower()
    # Doble sin pase (tela vieja "Doble $2000") se incluye.
    # Doble con pase distinto de 1er/1° (REPORTE PROGRAMA OFICIAL) se excluye.
    if low.startswith("doble"):
        if "pase" not in low and not PATRON_ULTIMO_PASE.search(nombre):
            return False
        if PATRON_PRIMER_PASE.search(nombre):
            return False
        return True
    if PATRON_EXCLUIR_PASE_SIN_FINAL.search(nombre):
        return True
    m_pase = PATRON_PASE_TELA.search(nombre)
    if m_pase and not PATRON_PRIMER_PASE.search(m_pase.group(2)):
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
    clave = nombre.lower()
    if clave in MAPEO_ABREVIATURAS:
        return MAPEO_ABREVIATURAS[clave]
    # Imperfecta / Imperfecta extra / Imperfecta(Extra) → IMP
    if "imperfecta" in clave:
        return "IMP"
    return MAPEO_ABREVIATURAS.get(clave.split()[0], nombre)


def es_tela_reporte_oficial(ruta_pdf: str | Path) -> bool:
    """REPORTE PROGRAMA OFICIAL con headers 'Na PREMIO/CLÁSICO'."""
    import pypdf
    try:
        reader = pypdf.PdfReader(ruta_pdf)
        if not reader.pages:
            return False
        muestra = ""
        for p in reader.pages[:4]:
            muestra += (p.extract_text() or "") + "\n"
        if not PATRON_PROGRAMA_OFICIAL_REPORTE.search(muestra):
            return False
        return bool(PATRON_CARRERA_TELA_REPORTE.search(muestra))
    except Exception:
        return False


def es_tela_oficial(ruta_pdf: str | Path) -> bool:
    """True si el PDF es un REPORTE PROGRAMA OFICIAL de San Isidro."""
    return es_tela_reporte_oficial(ruta_pdf)


def tipo_tela_oficial(ruta_pdf: str | Path) -> str | None:
    """Etiqueta de formato: PROGRAMA OFICIAL | None."""
    if es_tela_reporte_oficial(ruta_pdf):
        return "PROGRAMA OFICIAL"
    return None


def _segmento_entre_apuestas(
    paginas: list[list[str]],
    start_pi: int,
    start_li: int,
    end_pi: int,
    end_li: int,
) -> list[str]:
    """Lineas desde APUESTAS actual (inclusive) hasta el siguiente (exclusive), cross-page."""
    if start_pi == end_pi:
        return paginas[start_pi][start_li:end_li]
    lineas: list[str] = []
    lineas.extend(paginas[start_pi][start_li:])
    for pi in range(start_pi + 1, end_pi):
        lineas.extend(paginas[pi])
    if end_pi < len(paginas):
        lineas.extend(paginas[end_pi][:end_li])
    return lineas


_NOMBRES_BET_REPORTE = (
    r"Imperfecta(?:\s*\(?\s*extra\s*\)?)?"
    r"|Cuatrifecta|Ganador|Segundo|Tercero|Exacta|Trifecta|"
    r"Doble|Triplo|Cuaterna|Quintuplo|Cadena"
)
_PATRON_LINEA_BET_REPORTE = re.compile(
    rf"^({_NOMBRES_BET_REPORTE})\b(.*)$",
    re.IGNORECASE,
)
# Algunos exports (p. ej. 8248) pegan varias apuestas en una sola línea:
# "Tercero $2  Exacta $2.000" / "Ganador $2 Segundo $2"
_PATRON_INICIO_BET_REPORTE = re.compile(
    rf"(?i)({_NOMBRES_BET_REPORTE})\b"
)


def _partir_fragmentos_bet_reporte(linea: str) -> list[str]:
    """Parte una línea en fragmentos si hay varias apuestas concatenadas.

    Export Sabado: una apuesta por línea. Export 8248: varias en la misma
    (Ganador+Segundo, Tercero+Exacta, Cuaterna+Cadena, etc.).
    """
    s = linea.strip()
    if not s:
        return []
    matches = list(_PATRON_INICIO_BET_REPORTE.finditer(s))
    if not matches:
        return []
    frags: list[str] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(s)
        frag = s[m.start():end].strip()
        if frag:
            frags.append(frag)
    return frags


def _parsear_linea_bet_reporte(linea: str) -> tuple[str, str] | None:
    """Una línea 'Exacta $2.000' / 'Quintuplo 1° Pase$1.000' → (nombre, valor)."""
    s = linea.strip()
    if not s or not _PATRON_LINEA_BET_REPORTE.match(s):
        return None
    m_val = re.search(r"\$\s*([\d.,]+)", s)
    valor = m_val.group(1) if m_val else ""
    nombre = re.sub(r"\$\s*[\d.,]+", "", s).strip()
    if not nombre:
        return None
    return nombre, valor


def _parsear_bets_en_linea_reporte(linea: str) -> list[tuple[str, str]]:
    """Parsea una o más apuestas de una línea (soporta exports multilínea)."""
    out: list[tuple[str, str]] = []
    for frag in _partir_fragmentos_bet_reporte(linea):
        parsed = _parsear_linea_bet_reporte(frag)
        if parsed:
            out.append(parsed)
    return out


def _extraer_bloque_apuestas_reporte(race_lines: list[str]) -> list[str]:
    """Líneas de apuesta del segmento de carrera.

    pypdf puede partir el bloque: parte de las apuestas arriba y Exacta/TRI
    después de los caballos. Se toman todas las líneas que matchean apuesta,
    no solo el tramo contiguo tras ``APUESTAS``.
    """
    out: list[str] = []
    for l in race_lines:
        s = l.strip()
        if not s:
            continue
        if _PATRON_LINEA_BET_REPORTE.match(s):
            out.append(s)
    return out


_PATRON_DORSAL_GRILLA = re.compile(
    r"(?:Debuta|\d[A-Z]{2,4}|\)|\s|^)\s?(0[1-9]|1\d|2[0-4])\s?[A-Z(ÁÉÍÓÚÑ']"
)
# Dorsal en CHAQUETILLAS: "- 05 - colores" (la edad de la grilla es "- 5 -", un dígito).
_PATRON_DORSAL_CHAQUETILLA = re.compile(r"-\s*(\d{2})\s*-")


def _es_fin_chaquetillas(linea: str) -> bool:
    s = linea.strip()
    su = s.upper()
    if (
        PATRON_CARRERA_TELA_REPORTE.match(s)
        or su.startswith("BOLSA")
        or su.startswith("APUESTAS")
        or su == "SUPLENTES"
        or su.startswith("STUD 4")
        or "CABALLO" in su
        or "CHAQUETILLAS" in su
    ):
        return True
    return bool(_PATRON_DORSAL_GRILLA.search(s)) and not _PATRON_DORSAL_CHAQUETILLA.search(s)


def _bloques_caballos_programa_oficial(lineas: list[str]) -> list[list[str]]:
    """Parte el documento en bloques 'grilla → SUPLENTES → CHAQUETILLAS'.

    Cada carrera tiene exactamente un bloque y aparecen en el mismo orden que
    las carreras, aunque pypdf los ubique antes o después del header (o en otra
    página cuando hay dos carreras por hoja).
    """
    bloques: list[list[str]] = []
    inicio = 0
    i = 0
    while i < len(lineas):
        if "CHAQUETILLAS" not in lineas[i].upper():
            i += 1
            continue
        fin = i + 1
        while fin < len(lineas) and not _es_fin_chaquetillas(lineas[fin]):
            fin += 1
        bloques.append(lineas[inicio:fin])
        inicio = fin
        i = fin
    return bloques


def _caballos_bloque_programa_oficial(lineas: list[str]) -> int | None:
    """Caballos de una carrera a partir de su bloque de líneas.

    Fuente principal: dorsales de CHAQUETILLAS (puede seguir en varias líneas).
    Los dorsales listados bajo SUPLENTES no cuentan, salvo que también estén
    en la grilla de titulares. Sin CHAQUETILLAS se usa la grilla.
    Devuelve el dorsal máximo de los titulares.
    """
    grilla: set[int] = set()
    suplentes: set[int] = set()
    # pypdf corta CHAQUETILLAS entre el guion y el dorsal ("... verde -" / "15 - s/a"):
    # el regex se aplica sobre el texto unido, no línea por línea.
    texto_chaquetillas: list[str] = []
    zona = "grilla"
    for linea in lineas:
        s = linea.strip()
        su = s.upper()
        if "CHAQUETILLAS" in su:
            zona = "chaquetillas"
            s = s[su.index("CHAQUETILLAS") + len("CHAQUETILLAS"):]
        elif su == "SUPLENTES":
            zona = "suplentes"
            continue
        elif zona == "chaquetillas" and _es_fin_chaquetillas(s):
            zona = "grilla"

        if zona == "chaquetillas":
            texto_chaquetillas.append(s)
            continue
        destino = suplentes if zona == "suplentes" else grilla
        for m in _PATRON_DORSAL_GRILLA.finditer(s):
            num = int(m.group(1))
            if 1 <= num <= 24:
                destino.add(num)

    chaquetillas = {
        int(m.group(1))
        for m in _PATRON_DORSAL_CHAQUETILLA.finditer(" ".join(texto_chaquetillas))
        if 1 <= int(m.group(1)) <= 24
    }
    if chaquetillas:
        titulares = {n for n in chaquetillas if n not in suplentes or n in grilla}
    else:
        titulares = grilla
    return max(titulares) if titulares else None


def _obtener_apuestas_tela_reporte_oficial(ruta_pdf: str | Path) -> list[list]:
    """Parser REPORTE PROGRAMA OFICIAL (apuestas multilínea, Na PREMIO/CLÁSICO)."""
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    paginas = [(p.extract_text() or "").split("\n") for p in reader.pages]

    headers: list[tuple[int, int, int]] = []
    for pi, lineas in enumerate(paginas):
        for li, l in enumerate(lineas):
            m = PATRON_CARRERA_TELA_REPORTE.match(l.strip())
            if m:
                headers.append((pi, li, int(m.group(1))))
    headers_por_pagina: dict[int, int] = {}
    for pi, _, _ in headers:
        headers_por_pagina[pi] = headers_por_pagina.get(pi, 0) + 1
    bloques = _bloques_caballos_programa_oficial([l for pag in paginas for l in pag])
    bloques_por_orden = len(bloques) == len(headers)

    resultado: list[list] = []
    for idx, (start_pi, start_li, num_carrera) in enumerate(headers):
        if idx + 1 < len(headers):
            end_pi, end_li, _ = headers[idx + 1]
        else:
            end_pi = len(paginas) - 1
            end_li = len(paginas[end_pi]) if paginas else 0

        race_lines = _segmento_entre_apuestas(paginas, start_pi, start_li, end_pi, end_li)

        if bloques_por_orden:
            lineas_caballos = bloques[idx]
        elif headers_por_pagina[start_pi] == 1:
            lineas_caballos = paginas[start_pi]
        else:
            lineas_caballos = race_lines
        num_caballos = _caballos_bloque_programa_oficial(lineas_caballos) or 0

        apuestas_vistas: set[str] = set()
        for linea in _extraer_bloque_apuestas_reporte(race_lines):
            for nombre, valor in _parsear_bets_en_linea_reporte(linea):
                if not valor:
                    continue
                if es_apuesta_excluida(nombre):
                    continue
                codigo = abreviar_apuesta(normalizar_nombre_apuesta(nombre))
                if not codigo or codigo not in CODIGOS_APUESTA_VALIDOS:
                    continue
                if codigo in apuestas_vistas:
                    continue
                if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                    valor = ""
                resultado.append([num_carrera, num_caballos, codigo, valor])
                apuestas_vistas.add(codigo)

    return resultado


_PATRON_FIN_ENCABEZADO_TELA = re.compile(
    r"^(Premio\b|APUESTAS?\s*:|Carrera\b)",
    re.IGNORECASE,
)

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parsear_info_reunion_tela(texto_pagina: str) -> dict[str, str]:
    """Extrae reunión/fecha/hipódromo del encabezado de tela (no fechas del cuerpo)."""
    reunion = ""
    fecha = ""
    hipodromo = ""
    texto = texto_pagina or ""

    m_reun_rep = PATRON_REUNION_TELA_REPORTE.search(texto)
    if m_reun_rep:
        reunion = m_reun_rep.group(1)

    m_fecha_es = re.search(
        r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
        texto,
        re.IGNORECASE,
    )
    if m_fecha_es and not fecha:
        mes = _MESES_ES.get(m_fecha_es.group(2).lower())
        if mes:
            fecha = f"{int(m_fecha_es.group(1)):02d}/{mes:02d}/{m_fecha_es.group(3)}"

    for line in texto.split("\n"):
        s = line.strip()
        if not s:
            continue
        if _PATRON_FIN_ENCABEZADO_TELA.match(s):
            break
        if not reunion:
            m = re.search(r"Reunion\s+(\d+)", s, re.IGNORECASE)
            if m:
                reunion = m.group(1)
        if not fecha:
            d = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", s)
            if d:
                fecha = d.group(1)
        if "Hipodromo" in s or "HIPÓDROMO" in s.upper() or "HIPODROMO" in s.upper():
            hipodromo = s

    if not hipodromo or "PROGRAMA" in hipodromo.upper() or len(hipodromo) > 80:
        m_hip = re.search(r"HIP[OÓ]DROMO\s+DE\s+SAN\s+ISIDRO", texto, re.IGNORECASE)
        if m_hip:
            hipodromo = "Hipódromo de San Isidro"

    return {"reunion": reunion, "fecha": fecha, "hipodromo": hipodromo}


def extraer_info_reunion_tela(ruta_pdf: str | Path) -> dict[str, str]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    texto = reader.pages[0].extract_text() or ""
    return _parsear_info_reunion_tela(texto)


def obtener_apuestas_por_carrera(ruta_pdf: str | Path) -> list[list]:
    """Extrae las apuestas de un REPORTE PROGRAMA OFICIAL de San Isidro."""
    if not es_tela_reporte_oficial(ruta_pdf):
        raise ValueError(
            f"{Path(ruta_pdf).name} no es un REPORTE PROGRAMA OFICIAL de San Isidro"
        )
    return _obtener_apuestas_tela_reporte_oficial(ruta_pdf)


def _extraer_pases_de_lineas(
    race_lines: list[str],
    num_carrera: int,
    resultado: dict[int, dict[str, set[str]]],
) -> None:
    pases_carrera: dict[str, set[str]] = {}
    for l in race_lines:
        s = l.strip()
        if not s or s == "CHAQUETILLAS":
            continue
        for m in PATRON_PASE_TELA.finditer(s):
            bet_raw = m.group(1).lower()
            pase_raw = m.group(2)
            pase_norm = _normalizar_pase(pase_raw)
            codigo = abreviar_apuesta(bet_raw)
            if codigo:
                pases_carrera.setdefault(codigo, set()).add(pase_norm)
    if pases_carrera:
        dest = resultado.setdefault(num_carrera, {})
        for codigo, pases_set in pases_carrera.items():
            dest.setdefault(codigo, set()).update(pases_set)


def _extraer_pases_tela_reporte(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    paginas = [(p.extract_text() or "").split("\n") for p in reader.pages]
    resultado: dict[int, dict[str, set[str]]] = {}

    headers: list[tuple[int, int, int]] = []
    for pi, lineas in enumerate(paginas):
        for li, l in enumerate(lineas):
            m = PATRON_CARRERA_TELA_REPORTE.match(l.strip())
            if m:
                headers.append((pi, li, int(m.group(1))))

    for idx, (start_pi, start_li, num_carrera) in enumerate(headers):
        if idx + 1 < len(headers):
            end_pi, end_li, _ = headers[idx + 1]
        else:
            end_pi = len(paginas) - 1
            end_li = len(paginas[end_pi]) if paginas else 0
        race_lines = _segmento_entre_apuestas(paginas, start_pi, start_li, end_pi, end_li)
        bloque = _extraer_bloque_apuestas_reporte(race_lines)
        _extraer_pases_de_lineas(bloque, num_carrera, resultado)

    return resultado


def extraer_pases_tela_oficial(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    """Extrae info de pases (1er.Pase, 2do.Pase, etc.) para apuestas pick.
    Retorna {num_carrera: {codigo: {pase_normalizado, ...}}}"""
    return _extraer_pases_tela_reporte(ruta_pdf)


def _normalizar_pase(pase: str) -> str:
    """Normaliza nombre de pase a formato consistente.
    1er. Pase  -> 1er.Pase
    1° Pase    -> 1er.Pase
    ultimo pase -> Ultimo Pase
    Útimo Pase  -> Ultimo Pase (variante PDF sin 'l')
    1er.Pase   -> 1er.Pase
    2do .pase  -> 2do.Pase
    2do.pa se  -> 2do.Pase"""
    if PATRON_ULTIMO_PASE.search(pase):
        return "Ultimo Pase"
    m_grado = re.search(r"(\d+)\s*[°ºª\ufffd]", pase)
    if m_grado:
        n = int(m_grado.group(1))
        mapping = {
            1: "1er.Pase", 2: "2do.Pase", 3: "3er.Pase",
            4: "4to.Pase", 5: "5to.Pase", 6: "6to.Pase",
        }
        if n in mapping:
            return mapping[n]
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
        else:
            resultado[num_carrera]["caballos"] = max(
                resultado[num_carrera]["caballos"], cantidad_caballos
            )
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
    for sufijo in (" acumulado", " corrida", " al reves", " atras"):
        if n.endswith(sufijo):
            n = n[:-len(sufijo)].strip()
            break
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
