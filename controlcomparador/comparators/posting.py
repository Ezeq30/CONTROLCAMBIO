# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import APUESTAS_SIN_COMPARAR_VALOR
from controlcomparador.parsers.posting import merge_posting_prices
from controlcomparador.parsers.report import normalizar_reporte_palermo


def comparar_posting_con_reporte(
    datos_posting: tuple[dict[int, dict[str, Optional[float]]], set[str]],
    ruta_reporte: str | Path,
) -> tuple[bool, list[str]]:
    valores_posting, codigos_all_posting = datos_posting
    valores_reporte, codigos_all_reporte = normalizar_reporte_palermo(ruta_reporte)

    diferencias: list[str] = []
    todas_las_carreras = set(valores_posting.keys()) | set(valores_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_posting = num_carrera in valores_posting
        tiene_reporte = num_carrera in valores_reporte
        if not tiene_posting:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero no en Posting Prices")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en Posting Prices pero no en reporte")
            continue

        aps_posting = set(valores_posting[num_carrera].keys())
        aps_reporte = set(valores_reporte[num_carrera].keys())
        solo_en_posting = aps_posting - aps_reporte
        solo_en_reporte = aps_reporte - aps_posting
        solo_en_posting -= codigos_all_posting
        solo_en_reporte -= codigos_all_reporte

        if solo_en_posting:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Posting Prices pero no en reporte: {', '.join(sorted(solo_en_posting))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en Posting Prices: {', '.join(sorted(solo_en_reporte))}"
            )

        for codigo in sorted(aps_posting & aps_reporte):
            v_p = valores_posting[num_carrera].get(codigo)
            v_r = valores_reporte[num_carrera].get(codigo)
            if v_p is None and v_r is None:
                continue
            if v_p is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} sin monto en Posting Prices pero con valor {v_r} en reporte")
                continue
            if v_r is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} con monto {v_p} en Posting Prices pero NULL en reporte")
                continue
            if abs(v_p - v_r) > 0.01:
                diferencias.append(f"Carrera {num_carrera}: valor de {codigo} difiere (Posting: {v_p}, Reporte: {v_r})")

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias


def comparar_oficial_con_posting(
    datos_pdf: dict,
    datos_posting: tuple[dict[int, dict[str, Optional[float]]], set[str]],
) -> tuple[bool, list[str]]:
    valores_posting, codigos_all_posting = datos_posting

    diferencias: list[str] = []
    todas_las_carreras = set(datos_pdf.keys()) | set(valores_posting.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_pdf = num_carrera in datos_pdf
        tiene_posting = num_carrera in valores_posting
        if not tiene_pdf:
            diferencias.append(f"Carrera {num_carrera}: presente en Posting pero no en Oficial")
            continue
        if not tiene_posting:
            diferencias.append(f"Carrera {num_carrera}: presente en Oficial pero no en Posting")
            continue

        aps_pdf = set(datos_pdf[num_carrera].get("apuestas", {}).keys())
        aps_posting = set(valores_posting[num_carrera].keys())
        solo_en_pdf = aps_pdf - aps_posting
        solo_en_posting = (aps_posting - aps_pdf) - codigos_all_posting

        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Oficial pero no en Posting: {', '.join(sorted(solo_en_pdf))}"
            )
        if solo_en_posting:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Posting pero no en Oficial: {', '.join(sorted(solo_en_posting))}"
            )

        for codigo in sorted(aps_pdf & aps_posting):
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                continue
            v_pdf = datos_pdf[num_carrera]["apuestas"].get(codigo)
            v_post = valores_posting[num_carrera].get(codigo)
            if v_pdf is None and v_post is None:
                continue
            if v_pdf is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} sin valor en Oficial pero con valor {v_post} en Posting")
                continue
            if v_post is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} con valor {v_pdf} en Oficial pero sin valor en Posting")
                continue
            if abs(v_pdf - v_post) > 0.01:
                diferencias.append(
                    f"Carrera {num_carrera}: valor de {codigo} difiere (Oficial: {v_pdf}, Posting: {v_post})"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias
