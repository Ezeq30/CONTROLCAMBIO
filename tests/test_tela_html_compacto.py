# -*- coding: utf-8 -*-
"""Tests: HTML resumen tela compacto (1 hoja, pases mínimos)."""

from pathlib import Path
from unittest.mock import patch

from controlcomparador.ui import tables


def _datos_reunion_64_pases():
    """Fixture simplificada Reunión 64: bases + 10 secuencias de pases."""
    datos = {}
    for n in range(1, 13):
        datos[n] = {
            "caballos": 10,
            "apuestas": {"EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0},
            "pases": {},
        }
    datos[2]["apuestas"]["CAD"] = 200.0
    datos[3]["apuestas"]["QTN"] = 500.0
    datos[4]["apuestas"].update({"IMP": 2000.0, "QTP": 1000.0, "CUA": 1000.0})
    datos[5]["apuestas"]["QTN"] = 1000.0
    datos[6]["apuestas"]["TPL"] = 2000.0
    datos[7]["apuestas"]["QTN"] = 2000.0
    datos[8]["apuestas"].update({"QTP": 1000.0, "CUA": 1000.0})
    datos[9]["apuestas"]["QTN"] = 2000.0
    datos[10]["apuestas"]["TPL"] = 5000.0
    datos[11]["apuestas"]["IMP"] = 2000.0
    datos[12]["apuestas"].update({"IMP": 5000.0, "CUA": 2000.0})

    def _pases_pick(codigo: str, starts: list[int], n_pases: int):
        nombres = tables.PASES_POR_APUESTA[codigo]
        for sc in starts:
            for i, nombre in enumerate(nombres):
                carrera = sc + i
                datos[carrera]["pases"].setdefault(codigo, set()).add(nombre)

    _pases_pick("CAD", [2], 6)
    _pases_pick("QTN", [1, 3, 5, 7, 9], 4)
    _pases_pick("QTP", [4, 8], 5)
    _pases_pick("TPL", [6, 10], 3)
    return datos


class TestEstadoPaseHtml:
    def test_completa_ok(self):
        texto, clase = tables._estado_pase_html(
            "1er.Pase(C1) → 2do.Pase(C2)", "[green]COMPLETA[/green]",
        )
        assert texto == "OK"
        assert clase == "ok"

    def test_incompleta_falta_corto(self):
        texto, clase = tables._estado_pase_html(
            "Falta: 2do.Pase, 3er.Pase", "[yellow]INCOMPLETA[/yellow]",
        )
        assert texto == "Falta: 2do, 3er"
        assert clase == "warn"


class TestExportarResumenHtmlCompacto:
    def _exportar(self, datos: dict, tmp_path: Path) -> str:
        pdf = tmp_path / "tela.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        salida = tmp_path / "resumen.html"
        info = {"reunion": "64", "fecha": "12/07/2026", "hipodromo": "Hipodromo de San Isidro"}
        with patch("controlcomparador.ui.tables.extraer_info_reunion_tela", return_value=info):
            tables.exportar_resumen_html(datos, pdf, salida)
        return salida.read_text(encoding="utf-8")

    def test_section_bases_columnas_izq_compactas(self, tmp_path: Path):
        html = self._exportar(_datos_reunion_64_pases(), tmp_path)
        assert "section-bases" in html
        assert "bases-wrap" in html
        assert "top-row" in html
        assert "table-layout: fixed" in html
        assert "width: 5em" in html
        assert "width: 5.5em" in html
        assert "grid-template-columns: 1fr 1fr" in html
        assert "align-items: stretch" in html
        assert ".top-row .panel-validaciones" in html

    def test_pases_tabla_minima_una_sola(self, tmp_path: Path):
        html = self._exportar(_datos_reunion_64_pases(), tmp_path)
        assert html.count('<table class="pases-table">') == 1
        assert "<th>Ap.</th><th>Carreras</th><th class=\"center\">Estado</th>" in html
        assert "<th>Detalle</th>" not in html
        assert "CONTROL DE PASES - QTN" not in html
        assert "1er.Pase(C" not in html
        assert ">OK</td>" in html

    def test_top_row_bases_y_bottom_reglas_pases(self, tmp_path: Path):
        html = self._exportar(_datos_reunion_64_pases(), tmp_path)
        assert "top-row" in html
        assert "panel-validaciones" in html
        assert "VALIDACIONES" in html
        assert "<th>Carrera</th><th>Caballos</th><th>Observación</th>" in html
        assert "bottom-grid" in html
        assert "panel-reglas" in html
        assert "panel-pases" in html
        assert "reglas-table" in html
        assert "resumen-total" in html
        assert " filas</span>" in html
        cuerpo = html.split("</style>", 1)[-1]
        assert "panel-validaciones" in cuerpo
        assert "<th>Carrera</th><th>Caballos</th><th>Observación</th>" in cuerpo
        idx_top = cuerpo.find('<div class="top-row">')
        idx_val = cuerpo.find("panel-validaciones")
        idx_resumen = cuerpo.find("resumen-box")
        idx_bottom = cuerpo.find("bottom-grid")
        assert 0 <= idx_top < idx_val < idx_resumen < idx_bottom

    def test_pases_incompleta_muestra_falta(self, tmp_path: Path):
        datos = {
            1: {
                "caballos": 8,
                "apuestas": {"QTN": 1000.0, "EXA": 2000.0, "TRI": 2000.0},
                "pases": {"QTN": {"1er.Pase"}},
            },
            2: {"caballos": 8, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}, "pases": {}},
            3: {"caballos": 8, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}, "pases": {}},
            4: {"caballos": 8, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}, "pases": {}},
        }
        html = self._exportar(datos, tmp_path)
        assert "Falta:" in html
        assert "INCOMPLETA" not in html
