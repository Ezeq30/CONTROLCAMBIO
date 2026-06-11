from unittest.mock import patch

from controlcomparador.comparators.laplata import comparar_planilla_con_reporte


def _mock_planilla_con_datos():
    return {
        1: {"caballos": 9, "apuestas": {"EXA": 500.0, "TRI": 1200.0, "CUA": 5000.0}},
        2: {"caballos": 7, "apuestas": {"EXA": 550.0, "TRI": 1300.0, "CUA": 5500.0}},
    }


def _mock_reporte_con_datos():
    return {
        1: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "TER": None, "QTN": None, "EXA": 500.0, "TRI": 1200.0, "CUA": 5000.0}},
        2: {"caballos": 7, "apuestas": {"GAN": None, "SEG": None, "TER": None, "QTN": None, "EXA": 550.0, "TRI": 1300.0, "CUA": 5500.0}},
    }


def _mock_reporte_sin_ignorados():
    return {
        1: {"caballos": 9, "apuestas": {"EXA": 500.0, "TRI": 1200.0, "CUA": 5000.0}},
        2: {"caballos": 7, "apuestas": {"EXA": 550.0, "TRI": 1300.0, "CUA": 5500.0}},
    }


class TestCompararPlanillaConReporte:

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_coincide_cuando_todo_igual(self, mock_reporte, mock_planilla):
        mock_planilla.return_value = _mock_planilla_con_datos()
        mock_reporte.return_value = _mock_reporte_con_datos()
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is True
        assert diferencias == []

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_ignora_gan_seg_ter_qtn_del_reporte(self, mock_reporte, mock_planilla):
        mock_planilla.return_value = _mock_planilla_con_datos()
        mock_reporte.return_value = _mock_reporte_con_datos()
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is True
        assert all("GAN" not in d for d in diferencias)
        assert all("SEG" not in d for d in diferencias)
        assert all("TER" not in d for d in diferencias)
        assert all("QTN" not in d for d in diferencias)

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_detecta_diferencia_valor_exa(self, mock_reporte, mock_planilla):
        plan = _mock_planilla_con_datos()
        rep = _mock_reporte_con_datos()
        rep[1]["apuestas"]["EXA"] = 999.0
        mock_planilla.return_value = plan
        mock_reporte.return_value = rep
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is False
        assert any("EXA" in d for d in diferencias)

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_detecta_caballos_diferentes(self, mock_reporte, mock_planilla):
        plan = _mock_planilla_con_datos()
        rep = _mock_reporte_con_datos()
        rep[1]["caballos"] = 99
        mock_planilla.return_value = plan
        mock_reporte.return_value = rep
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is False
        assert any("caballos" in d for d in diferencias)

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_planilla_vacia_retorna_falso(self, mock_reporte, mock_planilla):
        mock_planilla.return_value = {}
        mock_reporte.return_value = _mock_reporte_sin_ignorados()
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is False

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_reporte_vacio_retorna_falso(self, mock_reporte, mock_planilla):
        mock_planilla.return_value = _mock_planilla_con_datos()
        mock_reporte.return_value = {}
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is False
