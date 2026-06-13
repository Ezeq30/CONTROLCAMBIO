# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import APUESTAS_IGNORAR_LAPLATA
from controlcomparador.parsers.planilla import normalizar_planilla_laplata
from controlcomparador.parsers.report import normalizar_reporte, validar_pick_conflict


def comparar_planilla_con_reporte(
    ruta_xls: str | Path,
    ruta_reporte: str | Path,
) -> tuple[bool, list[str]]:
    datos_planilla = normalizar_planilla_laplata(ruta_xls)
    datos_reporte, codigos_con_all = normalizar_reporte(ruta_reporte)

    diferencias: list[str] = []
    diferencias.extend(validar_pick_conflict(datos_reporte))

    if not datos_planilla:
        return False, ["No se pudo leer la planilla o no contiene datos validos"]
    if not datos_reporte:
        return False, ["No se pudo leer el reporte o no contiene datos validos"]

    todas_las_carreras = set(datos_planilla.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_planilla = num_carrera in datos_planilla
        tiene_reporte = num_carrera in datos_reporte
        if not tiene_planilla:
            diferencias.append(f"Carrera {num_carrera}: presente en Reporte pero no en Planilla")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en Planilla pero no en Reporte")
            continue

        caballos_planilla = datos_planilla[num_carrera]["caballos"]
        caballos_reporte = datos_reporte[num_carrera]["caballos"]
        if caballos_planilla != caballos_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: cantidad de caballos difiere "
                f"(Planilla: {caballos_planilla}, Reporte: {caballos_reporte})"
            )

        apuestas_planilla = set(datos_planilla[num_carrera]["apuestas"].keys())
        apuestas_reporte = set(datos_reporte[num_carrera]["apuestas"].keys())
        solo_en_planilla = apuestas_planilla - apuestas_reporte
        solo_en_reporte = (apuestas_reporte - apuestas_planilla) - APUESTAS_IGNORAR_LAPLATA - codigos_con_all

        if solo_en_planilla:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Planilla pero no en Reporte: {', '.join(sorted(solo_en_planilla))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Reporte pero no en Planilla: {', '.join(sorted(solo_en_reporte))}"
            )

        apuestas_comunes = apuestas_planilla & apuestas_reporte
        for codigo in apuestas_comunes:
            if codigo in APUESTAS_IGNORAR_LAPLATA:
                continue
            valor_planilla = datos_planilla[num_carrera]["apuestas"][codigo]
            valor_reporte = datos_reporte[num_carrera]["apuestas"][codigo]
            if valor_planilla is not None and valor_reporte is not None:
                if abs(valor_planilla - valor_reporte) > 0.01:
                    diferencias.append(
                        f"Carrera {num_carrera}: valor de {codigo} es diferente (Planilla: {valor_planilla}, Reporte: {valor_reporte})"
                    )
            elif valor_planilla is not None and valor_reporte is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en Planilla figura {valor_planilla} pero en Reporte NULL"
                )
            elif valor_planilla is None and valor_reporte is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en Reporte figura {valor_reporte} pero en Planilla NULL"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias
