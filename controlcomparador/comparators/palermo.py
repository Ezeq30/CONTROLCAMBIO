# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.parsers.pdf import leer_palermo_desde_pdf
from controlcomparador.parsers.report import normalizar_reporte_palermo


def comparar_palermo(
    ruta_pdf_palermo: str | Path,
    ruta_reporte: str | Path,
    fecha_objetivo: Optional[str] = None,
    datos_pdf: Optional[dict] = None,
) -> tuple[bool, list[str], list[str], dict, dict]:
    if datos_pdf is None:
        datos_pdf = leer_palermo_desde_pdf(ruta_pdf_palermo)
    fechas = datos_pdf["fechas"]
    apuestas_por_fecha = datos_pdf["apuestas_por_fecha"]
    resumen_por_fecha = datos_pdf.get("resumen_por_fecha", {})

    if fecha_objetivo is None:
        apuestas_pdf: dict[int, dict[str, Optional[float]]] = {}
        for _, apuestas_carreras in apuestas_por_fecha.items():
            for carrera, apuestas in apuestas_carreras.items():
                if carrera not in apuestas_pdf:
                    apuestas_pdf[carrera] = {}
                apuestas_pdf[carrera].update(dict(apuestas))
    else:
        apuestas_pdf = {
            carrera: dict(apuestas)
            for carrera, apuestas in apuestas_por_fecha.get(fecha_objetivo, {}).items()
        }

    datos_reporte, _ = normalizar_reporte_palermo(ruta_reporte)

    if fecha_objetivo is not None:
        resumen_fecha = resumen_por_fecha.get(fecha_objetivo, {})
        codigos_all_si_unica = {"EXA", "TRI"}
        for codigo in codigos_all_si_unica:
            info = resumen_fecha.get(codigo)
            if not info:
                continue
            if info.get("conteo_lineas", 0) != 1:
                continue
            valor = info.get("valor")
            if valor is None:
                continue
            for carrera in datos_reporte.keys():
                if carrera not in apuestas_pdf:
                    apuestas_pdf[carrera] = {}
                if codigo not in apuestas_pdf[carrera]:
                    apuestas_pdf[carrera][codigo] = valor

    diferencias: list[str] = []
    todas_las_carreras = set(apuestas_pdf.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_pdf = num_carrera in apuestas_pdf
        tiene_reporte = num_carrera in datos_reporte
        if not tiene_pdf:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero sin apuestas en PDF de Palermo")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en PDF de Palermo pero no en reporte")
            continue

        apuestas_carrera_pdf = apuestas_pdf[num_carrera]
        apuestas_carrera_rep = datos_reporte[num_carrera]
        codigos_pdf = set(apuestas_carrera_pdf.keys())
        codigos_rep = set(apuestas_carrera_rep.keys())
        solo_en_pdf = codigos_pdf - codigos_rep
        solo_en_reporte = codigos_rep - codigos_pdf

        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en PDF de Palermo pero no en reporte: {', '.join(sorted(solo_en_pdf))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en PDF de Palermo: {', '.join(sorted(solo_en_reporte))}"
            )

        codigos_comunes = codigos_pdf & codigos_rep
        for codigo in codigos_comunes:
            valor_pdf = apuestas_carrera_pdf.get(codigo)
            valor_rep = apuestas_carrera_rep.get(codigo)
            if valor_pdf is None and valor_rep is None:
                continue
            if valor_pdf is None and valor_rep is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} sin monto en PDF de Palermo pero con valor {valor_rep} en reporte"
                )
                continue
            if valor_pdf is not None and valor_rep is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} con monto {valor_pdf} en PDF de Palermo pero NULL en reporte"
                )
                continue
            if abs(valor_pdf - valor_rep) > 0.01:
                diferencias.append(
                    f"Carrera {num_carrera}: monto de {codigo} difiere (PDF Palermo: {valor_pdf}, Reporte: {valor_rep})"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias, fechas, apuestas_pdf, datos_reporte


def comparar_oficial_palermo_con_reporte(
    apuestas_oficial: list[dict],
    ruta_reporte: str | Path,
    apuestas_referencia_pdf: Optional[dict] = None,
) -> tuple[bool, list[str]]:
    datos_reporte, codigos_con_all = normalizar_reporte_palermo(ruta_reporte)
    oficial_por_carrera: dict[int, set[str]] = {}
    for item in apuestas_oficial or []:
        c = int(item.get("carrera"))
        oficial_por_carrera[c] = set(item.get("apuestas") or [])

    diferencias: list[str] = []
    todas_las_carreras = set(oficial_por_carrera.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_oficial = num_carrera in oficial_por_carrera
        tiene_reporte = num_carrera in datos_reporte
        if not tiene_oficial:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero no en oficial")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en oficial pero no en reporte")
            continue

        aps_oficial = oficial_por_carrera[num_carrera]
        aps_reporte = set(datos_reporte[num_carrera].keys())
        solo_en_oficial = aps_oficial - aps_reporte
        solo_en_reporte = (aps_reporte - aps_oficial) - codigos_con_all

        if solo_en_oficial:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en oficial pero no en reporte: {', '.join(sorted(solo_en_oficial))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en oficial: {', '.join(sorted(solo_en_reporte))}"
            )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias
