# -*- coding: utf-8 -*-

import re

# Patrón para el título de carrera: "1ª - Premio FLOWING RYE 2013 - 14:05 hs."
PATRON_CARRERA_PDF = re.compile(
    r"(\d+)\s*[ªºa]\s*[-–]\s*(.+?)\s*[-–]\s*\d{1,2}\s*:\s*\d{2}\s*hs\.?",
    re.IGNORECASE | re.DOTALL,
)

# Patrón para cada apuesta: "Nombre Apuesta $ valor"
PATRON_APUESTA_VALOR = re.compile(
    r"(.+?)\s*\$\s*([\d.,]+)",
    re.IGNORECASE,
)

# Fragmento regex para "último pase" con variantes de encoding PDF (Útimo sin l, Último, etc.)
_PASE_ULTIMO_FRAGMENT = (
    r"ultimo"
    r"|[úuU\u00fa\u00da]timo"
    r"|[úuU\u00fa\u00da]?ltimo"
)
_PASE_ULTIMO_SUFFIX = rf"(?:{_PASE_ULTIMO_FRAGMENT})\s*\.?\s*p\s*a\s*s\s*e"

# Grado ordinal PDF (1°, 1º) y replacement char cuando pypdf corrompe ° → �
_PASE_GRADO = r"[°ºª\ufffd]"

# Apuestas a excluir: desde 2do pase en adelante (último flexible por encoding PDF)
# Incluye forma nueva "2° Pase" / "2� Pase" del REPORTE PROGRAMA OFICIAL.
PATRON_EXCLUIR_PASE_SIN_FINAL = re.compile(
    r"2do\s*\.?\s*p\s*a\s*s\s*e"
    r"|3er\s*\.?\s*p\s*a\s*s\s*e"
    r"|4to\s*\.?\s*p\s*a\s*s\s*e"
    r"|5to\s*\.?\s*p\s*a\s*s\s*e"
    r"|6to\s*\.?\s*p\s*a\s*s\s*e"
    rf"|2\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|3\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|4\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|5\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|6\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|{_PASE_ULTIMO_SUFFIX}",
    re.IGNORECASE,
)
PATRON_ULTIMO_PASE = re.compile(rf"\b{_PASE_ULTIMO_SUFFIX}\b", re.IGNORECASE)
PATRON_FINAL = re.compile(r"\bfinal\b|final\s*pase", re.IGNORECASE)
# 1er.Pase (tela vieja) y 1° / 1º / 1� Pase (REPORTE PROGRAMA OFICIAL)
PATRON_PRIMER_PASE = re.compile(
    rf"\b1(?:er|re)\s*\.?\s*p\s*a\s*s\s*e\b"
    rf"|\b1\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e\b",
    re.IGNORECASE,
)

# Fragmento de etiqueta de pase (1er / 2do / 1° / último)
_PASE_ETIQUETA = (
    r"1er\s*\.?\s*p\s*a\s*s\s*e|1re\s*\.?\s*p\s*a\s*s\s*e"
    rf"|1\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    r"|2do\s*\.?\s*p\s*a\s*s\s*e"
    rf"|2\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    r"|3er\s*\.?\s*p\s*a\s*s\s*e"
    rf"|3\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    r"|4to\s*\.?\s*p\s*a\s*s\s*e"
    rf"|4\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    r"|5to\s*\.?\s*p\s*a\s*s\s*e"
    rf"|5\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    r"|6to\s*\.?\s*p\s*a\s*s\s*e"
    rf"|6\s*{_PASE_GRADO}\s*\.?\s*p\s*a\s*s\s*e"
    rf"|{_PASE_ULTIMO_SUFFIX}"
)

# Patrón para detectar pases en tela oficial (Cuaterna 1er.Pase, Doble 1° Pase, etc.)
# "Selectiva/Selectivo", "Con Jackpot" y "(Final)" opcionales entre el nombre y el pase.
# jack\s*po\s*t: pypdf a veces parte "Jackpot" como "Jackpo t"
PATRON_PASE_TELA = re.compile(
    r"(cuaterna|quintuplo|triplo|cadena|doble)\s+"
    r"(?:con\s+jack\s*po\s*t\s+)?"
    r"(?:selectiv[oa]\s+)?"
    r"(?:\(\s*final\s*\)\s*|final\s+)?"
    rf"({_PASE_ETIQUETA})",
    re.IGNORECASE,
)

# Header de carrera en REPORTE PROGRAMA OFICIAL: "1a PREMIO …", "8a CLÁSICO …"
PATRON_CARRERA_TELA_REPORTE = re.compile(
    r"^(\d+)\s*[aªº]\s+(?:PREMIO|CL[AÁ]SICO|\S+)",
    re.IGNORECASE | re.MULTILINE,
)

# Dorsal "01 NOMBRE" o pegado "0SI02 NOMBRE" (evitar "- 01 -" de CHAQUETILLAS)
PATRON_DORSAL_TELA_REPORTE = re.compile(
    r"(?<![-–])(?<!\d)(0?[1-9]|1\d|2[0-4])\s+(?:[A-ZÁÉÍÓÚÑ]|')",
)

# Header de grilla ("STUD 4 ÚLTIMAS…CABALLO JOCKEY"); no nombres de stud ("STUD GRR")
PATRON_HEADER_STUD_TELA_REPORTE = re.compile(
    r"^STUD\s*4\b|ÚLTIMAS|ULTIMAS|CABALLO\s+JOCKEY",
    re.IGNORECASE,
)

# Orden de pases para validación de secuencias
ORDEN_PASES: list[str] = [
    "1er.Pase", "2do.Pase", "3er.Pase", "4to.Pase", "5to.Pase", "Ultimo Pase",
]
PASE_ORDER: dict[str, int] = {name: i + 1 for i, name in enumerate(ORDEN_PASES)}

# Apuestas pick y qué pases necesita cada una (en orden)
PASES_POR_APUESTA: dict[str, list[str]] = {
    "QTN": ["1er.Pase", "2do.Pase", "3er.Pase", "Ultimo Pase"],
    "QTP": ["1er.Pase", "2do.Pase", "3er.Pase", "4to.Pase", "Ultimo Pase"],
    "TPL": ["1er.Pase", "2do.Pase", "Ultimo Pase"],
    "CAD": ["1er.Pase", "2do.Pase", "3er.Pase", "4to.Pase", "5to.Pase", "Ultimo Pase"],
}

# Mapeo de abreviaturas
MAPEO_ABREVIATURAS: dict[str, str] = {
    "ganador": "GAN",
    "segundo": "SEG",
    "tercero": "TER",
    "exacta": "EXA",
    "trifecta": "TRI",
    "imperfecta": "IMP",
    "imperfecta extra": "IMP",
    "cuatrifecta": "CUA",
    "doble": "DOB",
    "triplo": "TPL",
    "cuaterna": "QTN",
    "quintuplo": "QTP",
    "cadena": "CAD",
}

CODIGOS_APUESTA_VALIDOS: set[str] = set(MAPEO_ABREVIATURAS.values())

# Mapeo de códigos RSM a códigos estándar
MAPEO_RSM: dict[str, str | None] = {
    "WPS": None,
    "EXA": "EXA",
    "TRI": "TRI",
    "IMP": "IMP",
    "DOB": "DOB",
    "TPL": "TPL",
    "QTN": "QTN",
    "QTP": "QTP",
    "CAD": "CAD",
    "CUA": "CUA",
}

# Mapeo RSM para Palermo / Posting Prices (sin WPS)
MAPEO_RSM_SIN_WPS: dict[str, str] = {
    "EXA": "EXA", "TRI": "TRI", "IMP": "IMP", "DOB": "DOB",
    "TPL": "TPL", "QTN": "QTN", "QTP": "QTP", "CAD": "CAD", "CUA": "CUA",
}

# Códigos que solo se comparan en existencia, no en valor
APUESTAS_SIN_COMPARAR_VALOR: set[str] = {"GAN", "SEG", "TER"}

# EXA/TRI extra en B.RSM/posting (ALL por comodidad): aviso cyan, no error.
# En Ap.R (AVAILABLE POOLS) cualquier extra, incluido EXA/TRI, sí es error.
APUESTAS_EXTRA_AVISO: frozenset[str] = frozenset({"EXA", "TRI"})

# Apuestas "pick" mutuamente excluyentes por carrera
APUESTAS_PICK: set[str] = {"TPL", "QTN", "QTP", "CAD"}

# Pares excluyentes por carrera (EXA+TRI e IMP+CUA SÍ pueden coexistir)
PARES_EXCLUYENTES: tuple[tuple[str, str], ...] = (
    ("EXA", "IMP"),
    ("TRI", "CUA"),
)
MSG_EXA_IMP_JUNTOS = "EXA e IMP no pueden estar juntas"
MSG_TRI_CUA_JUNTOS = "TRI y CUA no pueden estar juntas"

# Apuestas a ignorar en reporte para La Plata
APUESTAS_IGNORAR_LAPLATA: set[str] = {"GAN", "SEG", "TER", "QTN"}

# Orden lógico para mostrar apuestas
ORDEN_APUESTAS: list[str] = [
    "GAN", "SEG", "TER", "EXA", "IMP", "TRI", "DOB", "TPL", "QTN", "QTP", "CAD", "CUA",
]

# Patrón para líneas de carrera en reporte: "1  GAN SEG TER 1/9 1/9 ..."
PATRON_CARRERA_REPORTE = re.compile(
    r"^\s*(\d+)\s+([A-Z\s]+?)(?:\s+(?:\b(?:SCR|\d+/\d+|99)\b))+",
    re.MULTILINE | re.IGNORECASE,
)

# Patrón para códigos de apuesta en línea
PATRON_CODIGOS_LINEA = re.compile(r"\b(GAN|SEG|TER|EXA|TRI|IMP|DOB|TPL|QTN|QTP|CAD|CUA)\b")

# Patrón RSM TABLE
PATRON_RSM = re.compile(
    r"^\s*\d+\s+([^\s]+(?:[-\s,][^\s]+)*)\s+---\s+([A-Z]+)\s+TS\s+([\d.,]+)",
    re.MULTILINE,
)

# Patrón para números de caballo
PATRON_CABALLO = re.compile(r"^(\d{2})\s+[A-Z]", re.MULTILINE | re.IGNORECASE)

# Patrón para línea de apuestas en PDF
PATRON_LINEA_APUESTA = re.compile(
    r"\$|ganador|segundo|tercero|exacta|trifecta|imperfecta|cuatrifecta|doble|triplo|cuaterna|quintuplo|cadena",
    re.IGNORECASE,
)

# Patrón para fechas
PATRON_FECHA = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")

# Patrón para fila Palermo
PATRON_FILA_PALERMO = re.compile(r"(.+?)\(\s*[\$\s]*([\d.,]+)(?:\.-)?\s*\)\s+(.+)")

# Patrón para línea de apuesta oficial
PATRON_APUESTAS_A = re.compile(r"APUESTAS?\s+A\s*:?\s+(.+)", re.IGNORECASE)

# Patrón para encabezado de carrera en oficial
PATRON_CARRERA_OFICIAL = re.compile(r"^\s*(\d+)\s*[^0-9A-Za-z]?\s*Carrera\b", re.IGNORECASE)

# Patrón CARD DEFAULT MINIMUMS
PATRON_DEFAULT = re.compile(r"(GAN|SEG|TER|EXA|IMP|TRI|DOB|TPL|QTN|QTP|CAD|CUA)\s+([\d.,]+)")

# Patrón para detectar PDF Tela Oficial San Isidro (formato viejo)
PATRON_PROGRAMA_DEPURADO = re.compile(r"Programa\s+Depurado", re.IGNORECASE)

# Formato nuevo: REPORTE PROGRAMA OFICIAL (apuestas multilínea, pases 1° Pase)
PATRON_PROGRAMA_OFICIAL_REPORTE = re.compile(
    r"PROGRAMA\s+OFICIAL",
    re.IGNORECASE,
)
PATRON_REUNION_TELA_REPORTE = re.compile(
    r"Reuni[oó]n\s*N\s*[°ºª\ufffd]?\s*(\d+)",
    re.IGNORECASE,
)

# Símbolos de la UI (compatibles con Windows cp1252)
SYM_OK = "[OK]"
SYM_FAIL = "[ERR]"
SYM_ARROW = "->"
