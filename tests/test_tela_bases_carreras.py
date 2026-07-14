# -*- coding: utf-8 -*-
"""Tests: columna Carreras en resumen tela oficial — ALL solo EXA/TRI/IMP."""

import re
from pathlib import Path
from unittest.mock import patch

from controlcomparador.ui import tables


def _datos_reunion_11_carreras():
    """Mock: EXA/TRI en todas; CAD/QTP valor único en todas; DOB en 1-9 y 10."""
    datos = {}
    for n in range(1, 12):
        datos[n] = {
            "caballos": 8,
            "apuestas": {
                "EXA": 2000.0,
                "TRI": 2000.0,
                "CAD": 200.0,
                "QTP": 1000.0,
            },
        }
    for n in range(1, 10):
        datos[n]["apuestas"]["DOB"] = 2000.0
    datos[10]["apuestas"]["DOB"] = 5000.0
    return datos


class TestFormatCarrerasList:
    def test_exa_todas_carreras_usa_all(self):
        carreras = list(range(1, 12))
        assert tables._format_carreras_list(carreras, 11, "EXA") == "ALL"

    def test_tri_todas_carreras_usa_all(self):
        carreras = list(range(1, 12))
        assert tables._format_carreras_list(carreras, 11, "TRI") == "ALL"

    def test_imp_todas_carreras_usa_all(self):
        carreras = list(range(1, 12))
        assert tables._format_carreras_list(carreras, 11, "IMP") == "ALL"

    def test_cad_todas_carreras_lista_rango(self):
        carreras = list(range(1, 12))
        assert tables._format_carreras_list(carreras, 11, "CAD") == "1-11"

    def test_qtp_todas_carreras_lista_rango(self):
        carreras = list(range(1, 12))
        assert tables._format_carreras_list(carreras, 11, "QTP") == "1-11"

    def test_dob_parcial_mantiene_rango(self):
        assert tables._format_carreras_list(list(range(1, 10)), 11, "DOB") == "1-9"


class TestExportarResumenHtmlCarreras:
    def test_html_all_solo_exa_tri_imp(self, tmp_path: Path):
        datos = _datos_reunion_11_carreras()
        pdf = tmp_path / "tela.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        salida = tmp_path / "resumen.html"
        info = {"reunion": "62", "fecha": "08/07/2026", "hipodromo": "Hipodromo de San Isidro"}

        with patch(
            "controlcomparador.ui.tables.extraer_info_reunion_tela",
            return_value=info,
        ):
            tables.exportar_resumen_html(datos, pdf, salida)

        html = salida.read_text(encoding="utf-8")
        filas_bases = re.findall(
            r"<tr><td>([^<]*)</td><td class=\"bet\">([^<]*)</td>",
            html,
        )

        assert ("ALL", "EXA") in filas_bases
        assert ("ALL", "TRI") in filas_bases
        assert ("1-11", "CAD") in filas_bases
        assert ("1-11", "QTP") in filas_bases
        assert ("1-9", "DOB") in filas_bases
        assert ("10", "DOB") in filas_bases
        for carr, cod in filas_bases:
            if cod not in ("EXA", "TRI", "IMP"):
                assert carr != "ALL", f"{cod} no debe usar ALL"


def _datos_reunion_13_parcial():
    """Mock reunión 13: EXA/TRI en todas; CAD solo C2; QTP solo C4,C9."""
    datos = {}
    for n in range(1, 14):
        datos[n] = {"caballos": 8, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}}
    datos[2]["apuestas"]["CAD"] = 200.0
    datos[4]["apuestas"]["QTP"] = 1000.0
    datos[9]["apuestas"]["QTP"] = 1000.0
    return datos


class TestResumenBasesUnicas:
    def test_todas_cuando_cubre_toda_la_reunion(self):
        datos = _datos_reunion_11_carreras()
        grupos = tables._agrupar_bases_por_apuesta(datos)
        carreras = grupos[("EXA", 2000.0)]
        assert tables._texto_resumen_base_unica(carreras, "EXA", 2000.0) == "EXA: todas son de 2000"

    def test_unica_cuando_una_sola_carrera(self):
        datos = _datos_reunion_13_parcial()
        grupos = tables._agrupar_bases_por_apuesta(datos)
        assert tables._texto_resumen_base_unica(grupos[("CAD", 200.0)], "CAD", 200.0) == "CAD: unica de 200"

    def test_todas_cuando_varias_carreras_mismo_valor(self):
        datos = _datos_reunion_13_parcial()
        grupos = tables._agrupar_bases_por_apuesta(datos)
        assert tables._texto_resumen_base_unica(grupos[("QTP", 1000.0)], "QTP", 1000.0) == "QTP: todas son de 1000"

    def test_html_resumen_unica_vs_todas(self, tmp_path: Path):
        datos = _datos_reunion_13_parcial()
        pdf = tmp_path / "tela.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        salida = tmp_path / "resumen.html"
        info = {"reunion": "62", "fecha": "08/07/2026", "hipodromo": "Hipodromo de San Isidro"}

        with patch(
            "controlcomparador.ui.tables.extraer_info_reunion_tela",
            return_value=info,
        ):
            tables.exportar_resumen_html(datos, pdf, salida)

        html = salida.read_text(encoding="utf-8")
        assert "EXA: todas son de 2000" in html
        assert "TRI: todas son de 2000" in html
        assert "CAD: unica de 200" in html
        assert "QTP: todas son de 1000" in html
        assert "CAD: todas son de" not in html
        assert "resumen-total" in html
        assert " filas</span>" in html
