# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

import re

from controlcomparador.config import (
    PATRON_CARRERA_REPORTE,
    PATRON_CODIGOS_LINEA,
    PATRON_RSM,
    PATRON_DEFAULT,
    PATRON_CABALLO,
    MAPEO_RSM,
    APUESTAS_PICK,
)
from controlcomparador.utils.money import parsear_monto_str


def validar_pick_conflict(datos_reporte: dict[int, dict]) -> list[str]:
    """Verifica que ninguna carrera tenga dos apuestas pick (TPL, QTN, QTP, CAD) juntas.
    Estas apuestas son mutuamente excluyentes: solo una por carrera."""
    errores: list[str] = []
    for num_carrera in sorted(datos_reporte.keys()):
        apuestas = datos_reporte[num_carrera].get("apuestas", {})
        picks = [cod for cod in apuestas if cod in APUESTAS_PICK]
        if len(picks) > 1:
            errores.append(
                f"Carrera {num_carrera}: apuestas pick conflictivas ({', '.join(picks)})"
            )
    return errores


def expandir_race_map(race_map: str) -> list[int]:
    race_map = race_map.strip().upper()
    if race_map == "ALL":
        return list(range(1, 16))
    carreras: list[int] = []
    if "," in race_map:
        partes = race_map.split(",")
        for parte in partes:
            parte = parte.strip()
            if not parte:
                continue
            if "-" in parte:
                rango_parts = parte.split("-")
                if len(rango_parts) == 2:
                    try:
                        inicio = int(rango_parts[0].strip())
                        fin = int(rango_parts[1].strip())
                        carreras.extend(range(inicio, fin + 1))
                    except ValueError:
                        pass
            else:
                try:
                    carreras.append(int(parte))
                except ValueError:
                    pass
        return carreras
    if "-" in race_map:
        partes = race_map.split("-")
        if len(partes) == 2:
            try:
                inicio = int(partes[0].strip())
                fin = int(partes[1].strip())
                return list(range(inicio, fin + 1))
            except ValueError:
                pass
    try:
        return [int(race_map)]
    except ValueError:
        return []


def normalizar_reporte(ruta_reporte: str | Path) -> tuple[dict[int, dict], set[str]]:
    with open(ruta_reporte, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    resultado: dict[int, dict] = {}
    apuestas_por_carrera: dict[int, set[str]] = {}
    caballos_por_carrera: dict[int, int] = {}

    lineas = contenido.split("\n")
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        m = PATRON_CARRERA_REPORTE.match(linea)
        if m:
            num_carrera = int(m.group(1))
            caballos_named = len(PATRON_CABALLO.findall(linea))
            if caballos_named > 0:
                cantidad = caballos_named + len(
                    re.compile(r"\bSCR\b", re.IGNORECASE).findall(linea)
                )
            else:
                caballo_re = re.compile(
                    r"\b(?:SCR|\d+/\d+|99)\b", re.IGNORECASE
                )
                cantidad = len(caballo_re.findall(linea))
            caballos_por_carrera[num_carrera] = cantidad
            apuestas_en_linea = set(PATRON_CODIGOS_LINEA.findall(linea))
            if num_carrera not in apuestas_por_carrera:
                apuestas_por_carrera[num_carrera] = set()
            apuestas_por_carrera[num_carrera].update(apuestas_en_linea)
            j = i + 1
            max_lineas_siguientes = 15
            while j < len(lineas) and (j - (i + 1)) < max_lineas_siguientes:
                linea_siguiente = lineas[j]
                linea_stripped = linea_siguiente.strip()
                if not linea_stripped:
                    break
                if not (linea_siguiente.startswith(" ") or linea_siguiente.startswith("\t")):
                    break
                if re.match(r"^\s*\d+\s+", linea_siguiente):
                    break
                apuestas_adicionales = PATRON_CODIGOS_LINEA.findall(linea_siguiente)
                if apuestas_adicionales:
                    apuestas_por_carrera[num_carrera].update(apuestas_adicionales)
                j += 1
        i += 1

    valores_por_carrera: dict[int, dict[str, Optional[float]]] = {}
    codigos_con_all: set[str] = set()
    scr_patron = re.compile(r"\bSCR\b", re.IGNORECASE)

    inicio_rsm = contenido.find("RSM TABLE")
    if inicio_rsm != -1:
        seccion_rsm = contenido[inicio_rsm:]
        fin_rsm_1 = seccion_rsm.find("\n\n\n")
        fin_rsm_2 = seccion_rsm.find("TIM BETTING")
        fin_rsm = None
        if fin_rsm_1 != -1 and fin_rsm_2 != -1:
            fin_rsm = min(fin_rsm_1, fin_rsm_2)
        elif fin_rsm_1 != -1:
            fin_rsm = fin_rsm_1
        elif fin_rsm_2 != -1:
            fin_rsm = fin_rsm_2
        if fin_rsm is not None and fin_rsm != -1:
            seccion_rsm = seccion_rsm[:fin_rsm]
        carreras_reales_reporte = sorted(caballos_por_carrera.keys()) if caballos_por_carrera else []

        for m in PATRON_RSM.finditer(seccion_rsm):
            race_map = m.group(1).strip()
            tipo_rsm = m.group(2).strip()
            valor_str = m.group(3).strip()
            valor_float = parsear_monto_str(valor_str)
            if valor_float is None:
                continue
            codigo_apuesta = MAPEO_RSM.get(tipo_rsm)
            if not codigo_apuesta:
                continue
            es_all = race_map.upper() == "ALL"
            if es_all:
                carreras = list(carreras_reales_reporte) if carreras_reales_reporte else expandir_race_map(race_map)
                codigos_con_all.add(codigo_apuesta)
            else:
                carreras = expandir_race_map(race_map)
            for carrera in carreras:
                if carreras_reales_reporte and carrera not in carreras_reales_reporte:
                    continue
                if carrera not in valores_por_carrera:
                    valores_por_carrera[carrera] = {}
                valores_por_carrera[carrera][codigo_apuesta] = valor_float

    inicio_defaults = contenido.find("CARD DEFAULT MINIMUMS - ARS")
    if inicio_defaults != -1:
        seccion_defaults = contenido[inicio_defaults:inicio_defaults + 500]
        for m in PATRON_DEFAULT.finditer(seccion_defaults):
            codigo = m.group(1)
            valor_str = m.group(2)
            v = parsear_monto_str(valor_str)
            if v is not None:
                pass

    todas_las_carreras = set(caballos_por_carrera.keys()) | set(apuestas_por_carrera.keys()) | set(valores_por_carrera.keys())
    for num_carrera in sorted(todas_las_carreras):
        resultado[num_carrera] = {
            "caballos": caballos_por_carrera.get(num_carrera, 0),
            "apuestas": {},
        }
        apuestas_carrera = apuestas_por_carrera.get(num_carrera, set())
        valores_carrera = valores_por_carrera.get(num_carrera, {})
        for codigo in apuestas_carrera:
            if codigo in valores_carrera:
                resultado[num_carrera]["apuestas"][codigo] = valores_carrera[codigo]
            else:
                resultado[num_carrera]["apuestas"][codigo] = None
        for codigo, valor in valores_carrera.items():
            if codigo not in resultado[num_carrera]["apuestas"]:
                resultado[num_carrera]["apuestas"][codigo] = valor
    return resultado, codigos_con_all


def normalizar_reporte_palermo(ruta_reporte: str | Path) -> tuple[dict[int, dict[str, Optional[float]]], set[str]]:
    with open(ruta_reporte, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    inicio_rsm = contenido.find("RSM TABLE")
    if inicio_rsm == -1:
        return {}, set()
    seccion_rsm = contenido[inicio_rsm:]
    fin_rsm_1 = seccion_rsm.find("\n\n\n")
    fin_rsm_2 = seccion_rsm.find("TIM BETTING")
    fin_rsm = None
    if fin_rsm_1 != -1 and fin_rsm_2 != -1:
        fin_rsm = min(fin_rsm_1, fin_rsm_2)
    elif fin_rsm_1 != -1:
        fin_rsm = fin_rsm_1
    elif fin_rsm_2 != -1:
        fin_rsm = fin_rsm_2
    if fin_rsm is not None and fin_rsm != -1:
        seccion_rsm = seccion_rsm[:fin_rsm]

    from controlcomparador.config import MAPEO_RSM_SIN_WPS
    mapeo_rsm = MAPEO_RSM_SIN_WPS

    max_carrera = 0
    for m in PATRON_RSM.finditer(seccion_rsm):
        race_map = m.group(1).strip()
        if race_map.upper() == "ALL":
            continue
        carreras = expandir_race_map(race_map)
        if carreras:
            max_carrera = max(max_carrera, max(carreras))
    if max_carrera == 0:
        max_carrera = 15

    valores_por_carrera: dict[int, dict[str, Optional[float]]] = {}
    codigos_con_all: set[str] = set()
    for m in PATRON_RSM.finditer(seccion_rsm):
        race_map = m.group(1).strip()
        tipo_rsm = m.group(2).strip()
        valor_str = m.group(3).strip()
        codigo_apuesta = mapeo_rsm.get(tipo_rsm)
        if not codigo_apuesta:
            continue
        valor_float = parsear_monto_str(valor_str)
        if valor_float is None:
            continue
        es_all = race_map.upper() == "ALL"
        if es_all:
            carreras = list(range(1, max_carrera + 1))
            codigos_con_all.add(codigo_apuesta)
        else:
            carreras = expandir_race_map(race_map)
        for carrera in carreras:
            if carrera not in valores_por_carrera:
                valores_por_carrera[carrera] = {}
            valores_por_carrera[carrera][codigo_apuesta] = valor_float
    return valores_por_carrera, codigos_con_all


PATRON_FECHA_REPORTE = re.compile(r"PROGRAM DATE:\s*(\d{1,2})-(\w{3})-(\d{2,4})")

_MESES = {
    "JAN": "01", "FEB": "02", "MAR": "03", "ABR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AGO": "08", "SEP": "09", "SET": "09", "OCT": "10", "NOV": "11", "DIC": "12",
}


def extraer_fecha_reporte(ruta_reporte: str | Path) -> str | None:
    with open(ruta_reporte, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    m = PATRON_FECHA_REPORTE.search(contenido)
    if not m:
        return None
    dia, mes_txt, anio = m.group(1), m.group(2).upper(), m.group(3)
    mes = _MESES.get(mes_txt)
    if mes is None:
        return None
    if len(anio) == 2:
        anio = "20" + anio
    return f"{int(dia):02d}/{mes}/{anio}"
