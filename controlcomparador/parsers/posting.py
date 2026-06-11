# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import (
    PATRON_RSM,
    MAPEO_RSM_SIN_WPS,
)
from controlcomparador.parsers.report import expandir_race_map
from controlcomparador.utils.money import parsear_monto_str


def normalizar_posting_prices(ruta: str | Path) -> tuple[dict[int, dict[str, Optional[float]]], set[str]]:
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    inicio = contenido.find("CARD POSTING PRICES")
    if inicio == -1:
        return {}, set()
    seccion = contenido[inicio:]
    fin_1 = seccion.find("\n\n\n")
    fin_2 = seccion.find("TIM BETTING")
    fin = None
    if fin_1 != -1 and fin_2 != -1:
        fin = min(fin_1, fin_2)
    elif fin_1 != -1:
        fin = fin_1
    elif fin_2 != -1:
        fin = fin_2
    if fin is not None and fin != -1:
        seccion = seccion[:fin]

    max_carrera = 0
    for m in PATRON_RSM.finditer(seccion):
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
    for m in PATRON_RSM.finditer(seccion):
        race_map = m.group(1).strip()
        tipo = m.group(2).strip()
        valor_str = m.group(3).strip()
        codigo_apuesta = MAPEO_RSM_SIN_WPS.get(tipo)
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


def merge_posting_prices(rutas: list[str | Path]) -> tuple[dict[int, dict[str, Optional[float]]], set[str]]:
    valores_final: dict[int, dict[str, Optional[float]]] = {}
    codigos_all_final: set[str] = set()
    for ruta in rutas:
        valores, codigos_all = normalizar_posting_prices(ruta)
        for carrera, apuestas in valores.items():
            if carrera not in valores_final:
                valores_final[carrera] = {}
            valores_final[carrera].update(apuestas)
        codigos_all_final.update(codigos_all)
    return valores_final, codigos_all_final
