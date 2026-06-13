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

# Apuestas a excluir: desde 2do pase en adelante
PATRON_EXCLUIR_PASE_SIN_FINAL = re.compile(
    r"2do\.?\s*pase|3er\.?\s*pase|4to\.?\s*pase|5to\.?\s*pase|ultimo\s*pase",
    re.IGNORECASE,
)
PATRON_FINAL = re.compile(r"\bfinal\b|final\s*pase", re.IGNORECASE)
PATRON_PRIMER_PASE = re.compile(r"\b1er\.?\s*pase\b|\b1re\.?\s*pase\b", re.IGNORECASE)

# Mapeo de abreviaturas
MAPEO_ABREVIATURAS: dict[str, str] = {
    "ganador": "GAN",
    "segundo": "SEG",
    "tercero": "TER",
    "exacta": "EXA",
    "trifecta": "TRI",
    "imperfecta": "IMP",
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

# Patrón para detectar PDF Tela Oficial San Isidro
PATRON_PROGRAMA_DEPURADO = re.compile(r"Programa\s+Depurado", re.IGNORECASE)

# Símbolos de la UI (compatibles con Windows cp1252)
SYM_OK = "[OK]"
SYM_FAIL = "[ERR]"
SYM_ARROW = "->"
