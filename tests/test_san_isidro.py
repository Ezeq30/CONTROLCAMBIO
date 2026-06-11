from unittest.mock import patch

import pytest

from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte


def _mock_pdf_con_datos():
    return {
        1: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 500.0, "TRI": 1200.0}},
        2: {"caballos": 7, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 550.0, "TRI": 1300.0}},
    }


def _mock_reporte_con_datos():
    return {
        1: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 500.0, "TRI": 1200.0}},
        2: {"caballos": 7, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 550.0, "TRI": 1300.0}},
    }


def _mock_reporte_con_diferencias():
    return {
        1: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 500.0, "TRI": 9999.0}},
        2: {"caballos": 7, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 550.0}},
    }


class TestCompararPdfYReporte:

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_coincide_cuando_todo_igual(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = _mock_pdf_con_datos()
        mock_reporte.return_value = _mock_reporte_con_datos()
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is True
        assert diferencias == []

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_detecta_diferencia_en_valor_tri(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = _mock_pdf_con_datos()
        mock_reporte.return_value = _mock_reporte_con_diferencias()
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("TRI" in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_detecta_apuesta_faltante_en_reporte(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = _mock_pdf_con_datos()
        mock_reporte.return_value = _mock_reporte_con_diferencias()
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("TRI" in d and "Reporte" in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_no_compara_valor_de_gan_seg_ter(self, mock_reporte, mock_pdf):
        pdf = _mock_pdf_con_datos()
        pdf[1]["apuestas"]["GAN"] = 100.0
        rep = _mock_reporte_con_datos()
        rep[1]["apuestas"]["GAN"] = 200.0
        mock_pdf.return_value = pdf
        mock_reporte.return_value = rep
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is True
        assert all("GAN" not in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_detecta_carrera_solo_en_pdf(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {
            1: {"caballos": 9, "apuestas": {"EXA": 500.0}},
        }
        mock_reporte.return_value = {}
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("solo en PDF" in d or "presente en PDF" in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_detecta_carrera_solo_en_reporte(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {}
        mock_reporte.return_value = {
            1: {"caballos": 9, "apuestas": {"EXA": 500.0}},
        }
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("solo en Reporte" in d or "presente en Reporte" in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_detecta_diferencia_caballos(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {
            1: {"caballos": 9, "apuestas": {"EXA": 500.0}},
        }
        mock_reporte.return_value = {
            1: {"caballos": 10, "apuestas": {"EXA": 500.0}},
        }
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("caballos" in d for d in diferencias)
