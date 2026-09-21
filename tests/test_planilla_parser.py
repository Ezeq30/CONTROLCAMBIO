# -*- coding: utf-8 -*-

from pathlib import Path
from unittest.mock import MagicMock, patch

from controlcomparador.parsers.planilla import leer_planilla_laplata, mapear_apuesta_planilla

FIXTURES = Path(__file__).parent / "fixtures"


class TestMapearApuestaPlanilla:
    def test_cuaterna_y_cuatrifecta(self):
        assert mapear_apuesta_planilla("CUATERNA") == "QTN"
        assert mapear_apuesta_planilla("CUATRIFECTA") == "CUA"
        assert mapear_apuesta_planilla("CUATRIFECTA SUPER") == "CUA"

    def test_doble_desquite(self):
        assert mapear_apuesta_planilla("DOBLE DESQ.") == "DOB"


class TestLeerPlanillaLaplata:
    def test_fixture_cabecera_m_parsea_carreras(self):
        ruta = FIXTURES / "planilla_laplata_m_header.xls"
        assert ruta.exists(), "falta fixture planilla_laplata_m_header.xls"
        datos = leer_planilla_laplata(ruta)
        assert sorted(datos.keys()) == list(range(1, 14))
        assert datos[1]["caballos"] == 9
        assert datos[1]["apuestas"]["EXA"] == 500.0
        assert datos[1]["apuestas"]["DOB"] == 1000.0
        assert datos[1]["apuestas"]["TRI"] == 500.0
        assert datos[1]["apuestas"]["QTN"] == 500.0
        assert datos[13]["caballos"] == 16
        assert datos[13]["apuestas"]["IMP"] == 1000.0
        assert datos[13]["apuestas"]["CUA"] == 500.0

    def test_cabecera_man_sigue_funcionando(self):
        """Regresión: header clásico MAN + CAR."""
        sheet = MagicMock()
        sheet.nrows = 3
        sheet.ncols = 6

        def cell_value(row, col):
            tabla = {
                (0, 0): "MAN",
                (0, 1): "CAR",
                (0, 2): "APUESTA",
                (0, 3): "BASE",
                (0, 4): "APUESTA",
                (0, 5): "BASE",
                (1, 0): 8.0,
                (1, 1): "1ª",
                (1, 2): "EXACTA",
                (1, 3): 500.0,
                (1, 4): "TRIFECTA",
                (1, 5): 500.0,
                (2, 0): "",
                (2, 1): "",
                (2, 2): "",
                (2, 3): "",
                (2, 4): "",
                (2, 5): "",
            }
            return tabla.get((row, col), "")

        sheet.cell_value.side_effect = cell_value
        wb = MagicMock()
        wb.sheet_by_index.return_value = sheet

        with patch("xlrd.open_workbook", return_value=wb):
            datos = leer_planilla_laplata("dummy.xls")

        assert datos[1]["caballos"] == 8
        assert datos[1]["apuestas"] == {"EXA": 500.0, "TRI": 500.0}
