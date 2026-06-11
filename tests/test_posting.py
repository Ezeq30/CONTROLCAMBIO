from unittest.mock import patch

from controlcomparador.comparators.posting import comparar_posting_con_reporte
from controlcomparador.parsers.posting import merge_posting_prices


def _datos_posting_sin_all():
    return {1: {"EXA": 500.0, "TRI": 1200.0}, 2: {"EXA": 550.0, "TRI": 1300.0}}, set()


def _datos_posting_con_all():
    return {1: {"EXA": 500.0, "TRI": 1200.0, "IMP": 2500.0}, 2: {"EXA": 550.0, "TRI": 1300.0, "IMP": 2500.0}}, {"IMP"}


def _datos_reporte_sin_all():
    return {1: {"EXA": 500.0, "TRI": 1200.0}, 2: {"EXA": 550.0, "TRI": 1300.0}}, set()


def _datos_reporte_con_all():
    return {1: {"EXA": 500.0, "TRI": 1200.0, "DOB": 3000.0}, 2: {"EXA": 550.0, "TRI": 1300.0, "DOB": 3000.0}}, {"DOB"}


class TestCompararPostingConReporte:

    @patch("controlcomparador.comparators.posting.normalizar_reporte_palermo")
    def test_coincide_cuando_todo_igual(self, mock_reporte):
        mock_reporte.return_value = _datos_reporte_sin_all()
        coincide, diferencias = comparar_posting_con_reporte(
            _datos_posting_sin_all(), "reporte"
        )
        assert coincide is True
        assert diferencias == []

    @patch("controlcomparador.comparators.posting.normalizar_reporte_palermo")
    def test_detecta_diferencia_valor(self, mock_reporte):
        rep = _datos_reporte_sin_all()
        rep[0][1]["EXA"] = 999.0
        mock_reporte.return_value = rep
        coincide, diferencias = comparar_posting_con_reporte(
            _datos_posting_sin_all(), "reporte"
        )
        assert coincide is False
        assert any("EXA" in d for d in diferencias)

    @patch("controlcomparador.comparators.posting.normalizar_reporte_palermo")
    def test_excluye_codigos_con_all_de_posting(self, mock_reporte):
        mock_reporte.return_value = _datos_reporte_sin_all()
        coincide, diferencias = comparar_posting_con_reporte(
            _datos_posting_con_all(), "reporte"
        )
        assert coincide is True
        assert all("IMP" not in d for d in diferencias)

    @patch("controlcomparador.comparators.posting.normalizar_reporte_palermo")
    def test_excluye_codigos_con_all_de_reporte(self, mock_reporte):
        mock_reporte.return_value = _datos_reporte_con_all()
        posting = {1: {"EXA": 500.0, "TRI": 1200.0}, 2: {"EXA": 550.0, "TRI": 1300.0}}, set()
        coincide, diferencias = comparar_posting_con_reporte(posting, "reporte")
        assert coincide is True
        assert all("DOB" not in d for d in diferencias)

    @patch("controlcomparador.comparators.posting.normalizar_reporte_palermo")
    def test_solo_en_posting_sin_all_se_detecta(self, mock_reporte):
        mock_reporte.return_value = _datos_reporte_sin_all()
        posting = {1: {"EXA": 500.0, "TRI": 1200.0, "IMP": 2500.0}, 2: {"EXA": 550.0, "TRI": 1300.0}}, set()
        coincide, diferencias = comparar_posting_con_reporte(posting, "reporte")
        assert coincide is False
        assert any("IMP" in d for d in diferencias)


class TestMergePostingPrices:

    def test_merge_con_un_solo_archivo(self, ruta_reporte_posting):
        valores, codigos_all = merge_posting_prices([ruta_reporte_posting])
        assert len(valores) > 0

    def test_merge_detecta_codigos_all(self, ruta_reporte_posting):
        _, codigos_all = merge_posting_prices([ruta_reporte_posting])
        assert "IMP" in codigos_all

    def test_segundo_archivo_sobrescribe_al_primero(self, tmp_path):
        primero = tmp_path / "a.txt"
        segundo = tmp_path / "b.txt"
        primero.write_text("CARD POSTING PRICES\n  1 1 --- EXA TS 100.00\n\n\n")
        segundo.write_text("CARD POSTING PRICES\n  1 1 --- EXA TS 200.00\n\n\n")
        valores, _ = merge_posting_prices([str(primero), str(segundo)])
        assert valores[1]["EXA"] == 200.0
