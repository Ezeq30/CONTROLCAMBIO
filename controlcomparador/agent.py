# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte
from controlcomparador.comparators.palermo import comparar_palermo, comparar_oficial_palermo_con_reporte
from controlcomparador.comparators.laplata import comparar_planilla_con_reporte
from controlcomparador.comparators.posting import comparar_posting_con_reporte, comparar_oficial_con_posting
from controlcomparador.parsers.pdf import (
    obtener_apuestas_por_carrera,
    normalizar_pdf,
    es_tela_oficial,
    leer_palermo_desde_pdf,
    extraer_apuestas_desde_oficial_palermo,
)
from controlcomparador.parsers.report import (
    normalizar_reporte,
    normalizar_reporte_palermo,
    extraer_fecha_reporte,
)
from controlcomparador.parsers.posting import merge_posting_prices
from controlcomparador.parsers.planilla import normalizar_planilla_laplata


def _normalizar_fecha_slash(fecha: str) -> str | None:
    """Normaliza ``d/m/yyyy`` o ``dd/mm/yyyy`` a ``dd/mm/yyyy``."""
    partes = fecha.strip().split("/")
    if len(partes) != 3:
        return None
    try:
        return f"{int(partes[0]):02d}/{int(partes[1]):02d}/{partes[2]}"
    except ValueError:
        return None


def _resolver_fecha_palermo(
    fechas: list[str],
    ruta_reporte: str | Path,
    fecha_objetivo: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Elige una sola fecha del PDF de bases.

    Retorna ``(fecha_usada, aviso)``. Nunca deja ``None`` si hay fechas en el PDF
    (evita fusionar varias reuniones).
    """
    if fecha_objetivo is not None:
        return fecha_objetivo, None
    if not fechas:
        return None, None
    if len(fechas) == 1:
        return fechas[0], None

    fecha_reporte = extraer_fecha_reporte(ruta_reporte)
    if fecha_reporte:
        ref_norm = _normalizar_fecha_slash(fecha_reporte)
        if ref_norm:
            for f in fechas:
                if _normalizar_fecha_slash(f) == ref_norm:
                    return f, None

    aviso = (
        f"No se pudo matchear la fecha del reporte con las del PDF "
        f"({', '.join(fechas)}); usando {fechas[0]}"
    )
    return fechas[0], aviso


class AgenteComparacion:
    def comparar_san_isidro(self, ruta_pdf: str | Path, ruta_reporte: str | Path) -> dict:
        apuestas = obtener_apuestas_por_carrera(ruta_pdf)
        coincide, diferencias, avisos = comparar_pdf_y_reporte(
            ruta_pdf, ruta_reporte, apuestas_raw=apuestas,
        )
        datos_reporte, _ = normalizar_reporte(ruta_reporte)
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "avisos": avisos,
            "datos_pdf": normalizar_pdf(ruta_pdf, apuestas_raw=apuestas),
            "datos_reporte": datos_reporte,
            "fecha_reporte": extraer_fecha_reporte(ruta_reporte),
            "tipo_pdf": "TELA OFICIAL" if es_tela_oficial(ruta_pdf) else "OFICIAL",
        }

    def comparar_palermo(
        self,
        ruta_pdf_palermo: str | Path,
        ruta_reporte: str | Path,
        fecha_objetivo: Optional[str] = None,
    ) -> dict:
        datos_pdf = leer_palermo_desde_pdf(ruta_pdf_palermo)
        fechas = datos_pdf.get("fechas", [])
        fecha_usada, aviso_fecha = _resolver_fecha_palermo(fechas, ruta_reporte, fecha_objetivo)
        coincide, diferencias, fechas_detectadas, apuestas_pdf_tabla, datos_reporte_tabla = comparar_palermo(
            ruta_pdf_palermo, ruta_reporte,
            fecha_objetivo=fecha_usada, datos_pdf=datos_pdf,
        )
        if aviso_fecha:
            diferencias = [aviso_fecha, *diferencias]
            coincide = False
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "fechas_detectadas": fechas_detectadas,
            "fecha_usada": fecha_usada,
            "datos_pdf": apuestas_pdf_tabla,
            "datos_reporte": (datos_reporte_tabla, set()),
        }

    def comparar_palermo_con_oficial(
        self,
        ruta_pdf_palermo: str | Path,
        ruta_reporte: str | Path,
        ruta_pdf_oficial: str | Path,
        fecha_objetivo: Optional[str] = None,
    ) -> dict:
        datos_pdf = leer_palermo_desde_pdf(ruta_pdf_palermo)
        fechas = datos_pdf.get("fechas", [])
        fecha_usada, aviso_fecha = _resolver_fecha_palermo(fechas, ruta_reporte, fecha_objetivo)
        coincide_pal, diferencias_pal, _, apuestas_pdf_tabla, datos_reporte_tabla = comparar_palermo(
            ruta_pdf_palermo, ruta_reporte,
            fecha_objetivo=fecha_usada, datos_pdf=datos_pdf,
        )
        if aviso_fecha:
            diferencias_pal = [aviso_fecha, *diferencias_pal]
            coincide_pal = False
        apuestas_oficial = extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial)
        apuestas_pdf_ref = datos_pdf.get("apuestas_por_fecha", {}).get(fecha_usada, {}) if fecha_usada else {}
        coincide_oficial, diferencias_oficial = comparar_oficial_palermo_con_reporte(
            apuestas_oficial, ruta_reporte,
            apuestas_referencia_pdf=apuestas_pdf_ref,
        )
        return {
            "palermo_vs_reporte": {
                "coincide": coincide_pal,
                "diferencias": diferencias_pal,
                "fechas_detectadas": fechas,
                "fecha_usada": fecha_usada,
                "datos_pdf": apuestas_pdf_tabla,
                "datos_reporte": (datos_reporte_tabla, set()),
            },
            "oficial_vs_reporte": {
                "coincide": coincide_oficial,
                "diferencias": diferencias_oficial,
                "apuestas_oficial": apuestas_oficial,
            },
        }

    def comparar_posting(self, rutas_posting: list[str | Path], ruta_reporte: str | Path) -> dict:
        datos_posting = merge_posting_prices(rutas_posting)
        coincide, diferencias = comparar_posting_con_reporte(datos_posting, ruta_reporte)
        return {"coincide": coincide, "diferencias": diferencias, "datos_posting": datos_posting}

    def comparar_oficial_posting(self, ruta_pdf: str | Path, rutas_posting: list[str | Path]) -> dict:
        apuestas = obtener_apuestas_por_carrera(ruta_pdf)
        datos_pdf = normalizar_pdf(ruta_pdf, apuestas_raw=apuestas)
        datos_posting = merge_posting_prices(rutas_posting)
        return self.comparar_oficial_posting_con_datos(datos_pdf, datos_posting)

    def comparar_oficial_posting_con_datos(
        self,
        datos_pdf: dict,
        datos_posting: tuple,
    ) -> dict:
        coincide, diferencias, avisos = comparar_oficial_con_posting(datos_pdf, datos_posting)
        return {"coincide": coincide, "diferencias": diferencias, "avisos": avisos}

    def comparar_laplata(self, ruta_xls: str | Path, ruta_reporte: str | Path) -> dict:
        coincide, diferencias = comparar_planilla_con_reporte(ruta_xls, ruta_reporte)
        datos_reporte, _ = normalizar_reporte(ruta_reporte)
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "datos_planilla": normalizar_planilla_laplata(ruta_xls),
            "datos_reporte": datos_reporte,
        }
