# -*- coding: utf-8 -*-
"""Columna Ap. en tabla SI: solo apuestas del PDF, no del reporte."""

from pathlib import Path

from controlcomparador.parsers.pdf import (
    es_tela_oficial,
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)
from controlcomparador.parsers.report import normalizar_reporte
from controlcomparador.ui.tables import imprimir_tabla_san_isidro


def _codigos_ap_por_carrera(html_buffer: list) -> dict[int, list[str]]:
    """Extrae códigos Ap. agrupados por carrera desde html_buffer."""
    por_carrera: dict[int, list[str]] = {}
    carrera_actual = None
    for fila in html_buffer[0]["filas"]:
        if fila[0]:
            carrera_actual = int(fila[0])
            por_carrera.setdefault(carrera_actual, [])
        if carrera_actual is not None:
            por_carrera[carrera_actual].append(fila[2])
    return por_carrera


class TestColumnaApSoloPdf:
    def test_c11_sin_exa_tri_si_no_estan_en_tela(self):
        """Reporte con ALL EXA/TRI no debe agregar filas Ap. si la tela no las tiene."""
        pdf = {
            11: {
                "caballos": 15,
                "apuestas": {
                    "GAN": None,
                    "SEG": None,
                    "TER": None,
                    "IMP": 2000.0,
                    "CUA": 2000.0,
                },
            },
        }
        rep = {
            11: {
                "caballos": 15,
                "apuestas": {
                    "GAN": None,
                    "SEG": None,
                    "TER": None,
                    "EXA": 2000.0,
                    "IMP": 2000.0,
                    "TRI": 2000.0,
                    "CUA": 2000.0,
                },
            },
        }
        buf: list = []
        imprimir_tabla_san_isidro(
            pdf, rep, tipo_pdf="TELA OFICIAL", imprimir=False, html_buffer=buf,
        )
        codigos = _codigos_ap_por_carrera(buf)[11]
        assert codigos == ["GAN", "SEG", "TER", "IMP", "CUA"]
        assert "EXA" not in codigos
        assert "TRI" not in codigos

    def test_archivos_reales_c11_si_existen(self):
        pdf_path = Path(
            r"c:\Users\cdiaz\Downloads\SI_PROGRAMA_OFICIAL_DEL_12-08-2026_"
            r"(Total_de_carreras_11)_8077.pdf"
        )
        rep_path = Path(r"c:\Users\cdiaz\Downloads\0811_143238_CardRpt.txt")
        if not pdf_path.is_file() or not rep_path.is_file():
            return
        assert es_tela_oficial(pdf_path)
        datos_pdf = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(pdf_path))
        datos_rep, _ = normalizar_reporte(rep_path)
        buf: list = []
        imprimir_tabla_san_isidro(
            datos_pdf, datos_rep, tipo_pdf="TELA OFICIAL", imprimir=False, html_buffer=buf,
        )
        codigos = _codigos_ap_por_carrera(buf)[11]
        assert "EXA" not in codigos
        assert "TRI" not in codigos
        assert "IMP" in codigos
        assert "CUA" in codigos
