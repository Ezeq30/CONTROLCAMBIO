# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional
import re

from controlcomparador.utils.money import parsear_monto_str


def mapear_apuesta_planilla(nombre: str) -> Optional[str]:
    if not nombre:
        return None
    texto = nombre.strip().upper()
    if "CUATRIFECTA SUPER" in texto:
        return "CUA"
    if "CUATRIFECTA" in texto:
        return "CUA"
    if "CUATERNA EXTRAORDINARIA" in texto or "CUATERNA EXT" in texto:
        return "QTN"
    if "CUATERNA" in texto:
        return "QTN"
    if "TRIPLO EXTRAORDINARIO" in texto or "TRIPLO EXTRA" in texto:
        return "TPL"
    if "TRIPLO" in texto:
        return "TPL"
    if "TRIFECTA" in texto:
        return "TRI"
    if "IMPERFECTA ESPECIAL" in texto or "IMPERFECTA ESP" in texto:
        return "IMP"
    if "IMPERFECTA" in texto:
        return "IMP"
    if "EXACTA" in texto:
        return "EXA"
    if "DOBLE DESQUITE" in texto or "DOBLE DESQ" in texto:
        return "DOB"
    if "DOBLE" in texto:
        return "DOB"
    if "QUINTUPLO" in texto:
        return "QTP"
    if "CADENA" in texto:
        return "CAD"
    return None


def leer_planilla_laplata(ruta: str | Path) -> dict[int, dict]:
    import xlrd
    wb = xlrd.open_workbook(str(ruta), formatting_info=False)
    sheet = wb.sheet_by_index(0)
    header_row = None
    man_idx = -1
    car_idx = -1
    for row in range(min(sheet.nrows, 200)):
        values = [str(sheet.cell_value(row, c)).strip().upper() for c in range(sheet.ncols)]
        for c, v in enumerate(values):
            if v == "MAN":
                man_idx = c
            if v == "CAR":
                car_idx = c
        if man_idx >= 0 and car_idx >= 0:
            header_row = row
            break
    if header_row is None:
        return {}
    resultado: dict[int, dict] = {}
    for row in range(header_row + 1, sheet.nrows):
        man_val = str(sheet.cell_value(row, man_idx)).strip()
        car_val = str(sheet.cell_value(row, car_idx)).strip()
        if not man_val or not car_val:
            continue
        m_car = re.match(r"(\d+)\s*[ªº]", car_val)
        if not m_car:
            continue
        num_carrera = int(m_car.group(1))
        try:
            caballos = int(float(man_val))
        except (ValueError, TypeError):
            continue
        apuestas: dict[str, Optional[float]] = {}
        bet_start = max(man_idx, car_idx) + 1
        for col in range(bet_start, sheet.ncols - 1, 2):
            if col + 1 >= sheet.ncols:
                break
            bet_name = str(sheet.cell_value(row, col)).strip()
            base_str = str(sheet.cell_value(row, col + 1)).strip()
            if not bet_name:
                continue
            codigo = mapear_apuesta_planilla(bet_name)
            if codigo is None:
                continue
            valor = parsear_monto_str(base_str.replace("$", "").strip())
            apuestas[codigo] = valor
        resultado[num_carrera] = {"caballos": caballos, "apuestas": apuestas}
    return resultado


def normalizar_planilla_laplata(ruta: str | Path) -> dict[int, dict]:
    return leer_planilla_laplata(ruta)
