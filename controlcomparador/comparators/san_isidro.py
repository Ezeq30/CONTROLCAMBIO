# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import APUESTAS_SIN_COMPARAR_VALOR, ORDEN_APUESTAS
from controlcomparador.parsers.pdf import normalizar_pdf
from controlcomparador.parsers.report import (
    bases_de_carrera,
    normalizar_reporte,
    validar_pick_conflict,
)


def mensaje_extra_ap_r(num_carrera: int, codigos) -> str:
    """Apuesta en AVAILABLE POOLS (Ap.R) que no está en el oficial."""
    vistos = set(codigos)
    ordenados = [c for c in ORDEN_APUESTAS if c in vistos]
    ordenados.extend(sorted(vistos - set(ordenados)))
    lista = ", ".join(ordenados)
    verbo = "está" if len(ordenados) == 1 else "están"
    return f"Carrera {num_carrera}: {lista} {verbo} de más en el reporte, no {verbo} en el oficial"


def comparar_pdf_y_reporte(
    ruta_pdf: str | Path,
    ruta_reporte: str | Path,
    apuestas_raw: Optional[list[list]] = None,
) -> tuple[bool, list[str], list[str]]:
    datos_pdf = normalizar_pdf(ruta_pdf, apuestas_raw=apuestas_raw)
    datos_reporte, _ = normalizar_reporte(ruta_reporte)
    diferencias: list[str] = []
    avisos: list[str] = []
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
        pools = set((datos_reporte[num_carrera].get("apuestas") or {}).keys())
        bases = bases_de_carrera(datos_reporte[num_carrera])
        solo_en_pdf = apuestas_pdf - pools
        solo_en_reporte = pools - apuestas_pdf

        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en PDF pero no en Reporte: {', '.join(sorted(solo_en_pdf))}"
            )
        if solo_en_reporte:
            diferencias.append(mensaje_extra_ap_r(num_carrera, solo_en_reporte))

        apuestas_comunes = apuestas_pdf & pools
        for codigo in apuestas_comunes:
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                continue
            valor_pdf = datos_pdf[num_carrera]["apuestas"][codigo]
            valor_reporte = bases.get(codigo)
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
    return coincide_todo, diferencias, avisos
