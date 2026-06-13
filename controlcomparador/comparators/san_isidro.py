# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import APUESTAS_SIN_COMPARAR_VALOR
from controlcomparador.parsers.pdf import normalizar_pdf
from controlcomparador.parsers.report import normalizar_reporte, validar_pick_conflict


def comparar_pdf_y_reporte(
    ruta_pdf: str | Path,
    ruta_reporte: str | Path,
    apuestas_raw: Optional[list[list]] = None,
) -> tuple[bool, list[str]]:
    datos_pdf = normalizar_pdf(ruta_pdf, apuestas_raw=apuestas_raw)
    datos_reporte, codigos_con_all = normalizar_reporte(ruta_reporte)
    diferencias: list[str] = []
    diferencias.extend(validar_pick_conflict(datos_reporte))
    todas_las_carreras = set(datos_pdf.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_pdf = num_carrera in datos_pdf
        tiene_reporte = num_carrera in datos_reporte
        if not tiene_pdf:
            diferencias.append(f"Carrera {num_carrera}: presente en Reporte pero no en PDF")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en PDF pero no en Reporte")
            continue

        caballos_pdf = datos_pdf[num_carrera]["caballos"]
        caballos_reporte = datos_reporte[num_carrera]["caballos"]
        if caballos_pdf != caballos_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: cantidad de caballos difiere "
                f"(PDF: {caballos_pdf}, Reporte: {caballos_reporte})"
            )

        apuestas_pdf = set(datos_pdf[num_carrera]["apuestas"].keys())
        apuestas_reporte = set(datos_reporte[num_carrera]["apuestas"].keys())
        solo_en_pdf = apuestas_pdf - apuestas_reporte
        solo_en_reporte = (apuestas_reporte - apuestas_pdf) - codigos_con_all

        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en PDF pero no en Reporte: {', '.join(sorted(solo_en_pdf))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Reporte pero no en PDF: {', '.join(sorted(solo_en_reporte))}"
            )

        apuestas_comunes = apuestas_pdf & apuestas_reporte
        for codigo in apuestas_comunes:
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                continue
            valor_pdf = datos_pdf[num_carrera]["apuestas"][codigo]
            valor_reporte = datos_reporte[num_carrera]["apuestas"][codigo]
            if valor_pdf is not None and valor_reporte is not None:
                if abs(valor_pdf - valor_reporte) > 0.01:
                    diferencias.append(
                        f"Carrera {num_carrera}: valor de {codigo} es diferente (PDF: {valor_pdf}, Reporte: {valor_reporte})"
                    )
            elif valor_pdf is not None and valor_reporte is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en el PDF figura {valor_pdf} pero en el reporte NULL"
                )
            elif valor_pdf is None and valor_reporte is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en el reporte figura {valor_reporte} pero en el PDF NULL"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias
