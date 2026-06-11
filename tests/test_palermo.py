from unittest.mock import patch

from controlcomparador.comparators.palermo import comparar_oficial_palermo_con_reporte


def _mock_reporte_sin_all():
    return {
        1: {"EXA": 500.0, "TRI": 1200.0},
        2: {"EXA": 550.0, "TRI": 1300.0},
    }, set()


def _mock_reporte_con_all_en_tri():
    return {
        1: {"EXA": 500.0, "TRI": 1200.0},
        2: {"EXA": 550.0, "TRI": 1300.0},
    }, {"TRI"}


class TestCompararOficialPalermoConReporte:

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_coincide_cuando_todo_igual(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_sin_all()
        oficial = [
            {"carrera": 1, "apuestas": ["EXA", "TRI"]},
            {"carrera": 2, "apuestas": ["EXA", "TRI"]},
        ]
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is True
        assert diferencias == []

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_detecta_apuesta_solo_en_oficial(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_sin_all()
        oficial = [
            {"carrera": 1, "apuestas": ["EXA", "TRI", "IMP"]},
        ]
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is False
        assert any("IMP" in d for d in diferencias)

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_excluye_codigos_con_all_de_solo_en_reporte(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_con_all_en_tri()
        oficial = [
            {"carrera": 1, "apuestas": ["EXA"]},
            {"carrera": 2, "apuestas": ["EXA"]},
        ]
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is True
        assert all("TRI" not in d for d in diferencias)

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_detecta_exa_sin_all_en_reporte(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_con_all_en_tri()
        oficial = [
            {"carrera": 1, "apuestas": ["IMP"]},
        ]
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is False

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_carrera_solo_en_oficial(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_sin_all()
        oficial = [
            {"carrera": 3, "apuestas": ["EXA"]},
        ]
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is False
        assert any("Carrera 3" in d for d in diferencias)

    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_carrera_solo_en_reporte(self, mock_reporte):
        mock_reporte.return_value = _mock_reporte_sin_all()
        oficial = []
        coincide, diferencias = comparar_oficial_palermo_con_reporte(oficial, "reporte")
        assert coincide is False
        assert any("Carrera 1" in d for d in diferencias)
