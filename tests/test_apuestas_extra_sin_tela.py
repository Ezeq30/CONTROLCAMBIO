# -*- coding: utf-8 -*-
"""EXA/TRI extra en Ap.R = error; extra ALL solo en posting/B.RSM."""

from pathlib import Path
from unittest.mock import patch

from controlcomparador.comparators.posting import comparar_oficial_con_posting
from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte
from controlcomparador.parsers.pdf import (
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)
from controlcomparador.parsers.report import normalizar_reporte


class TestApuestasExtraSinTela:
    def test_c4_c7_c11_all_en_bases_no_error_izq(self):
        """ALL EXA/TRI en RSM TABLE (bases), no en Ap.R → comparador izq sin error."""
        pdf = {
            4: {"caballos": 13, "apuestas": {"GAN": None, "IMP": 2000.0, "DOB": 2000.0, "QTN": 1000.0, "CUA": 1000.0}},
            7: {"caballos": 6, "apuestas": {"GAN": None, "EXA": 2000.0, "DOB": 2000.0, "QTP": 1000.0, "CUA": 1000.0}},
            11: {"caballos": 15, "apuestas": {"GAN": None, "IMP": 5000.0, "CUA": 2000.0}},
        }
        rep = {
            4: {
                "caballos": 13,
                "apuestas": {"GAN": None, "IMP": None, "DOB": None, "QTN": None, "CUA": None},
                "bases": {"EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 1000.0, "CUA": 1000.0},
            },
            7: {
                "caballos": 6,
                "apuestas": {"GAN": None, "EXA": None, "DOB": None, "QTP": None, "CUA": None},
                "bases": {"EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTP": 1000.0, "CUA": 1000.0},
            },
            11: {
                "caballos": 15,
                "apuestas": {"GAN": None, "IMP": None, "CUA": None},
                "bases": {"EXA": 2000.0, "IMP": 5000.0, "TRI": 2000.0, "CUA": 2000.0},
            },
        }
        with patch("controlcomparador.comparators.san_isidro.normalizar_pdf", return_value=pdf):
            with patch(
                "controlcomparador.comparators.san_isidro.normalizar_reporte",
                return_value=(rep, {"EXA", "TRI"}),
            ):
                coincide, diferencias, avisos = comparar_pdf_y_reporte("pdf", "reporte")

        assert coincide is True
        assert diferencias == []
        assert avisos == []

    def test_exa_tri_en_pools_es_error(self):
        """EXA/TRI en AVAILABLE POOLS y no en oficial → error, no aviso extra."""
        pdf = {
            10: {
                "caballos": 8,
                "apuestas": {"GAN": None, "EXA": 2000.0, "DOB": 2000.0, "CUA": 1000.0},
            },
        }
        rep = {
            10: {
                "caballos": 8,
                "apuestas": {"GAN": None, "EXA": None, "TRI": None, "DOB": None, "CUA": None},
                "bases": {"EXA": 2000.0, "DOB": 2000.0, "CUA": 1000.0},
            },
        }
        with patch("controlcomparador.comparators.san_isidro.normalizar_pdf", return_value=pdf):
            with patch(
                "controlcomparador.comparators.san_isidro.normalizar_reporte",
                return_value=(rep, set()),
            ):
                coincide, diferencias, avisos = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("TRI" in d and "reporte" in d and "oficial" in d for d in diferencias)
        assert not any("TRI" in a for a in avisos)

    def test_posting_exa_sin_tela_c4(self):
        pdf = {
            4: {
                "caballos": 12,
                "apuestas": {"GAN": None, "IMP": 2000.0, "DOB": 2000.0},
            },
        }
        posting = ({4: {"EXA": 2000.0, "TRI": 2000.0, "IMP": 2000.0, "DOB": 2000.0}}, {"EXA", "TRI"})
        coincide, diferencias, avisos = comparar_oficial_con_posting(pdf, posting)
        assert coincide is True
        assert diferencias == []
        assert any("Carrera 4" in a and "EXA" in a and "aviso" in a for a in avisos)
        assert any("Carrera 4" in a and "TRI" in a and "aviso" in a for a in avisos)

    def test_dob_extra_sigue_siendo_error(self):
        pdf = {1: {"caballos": 10, "apuestas": {"GAN": None, "EXA": 2000.0}}}
        rep = {1: {"caballos": 10, "apuestas": {"GAN": None, "EXA": 2000.0, "DOB": 2000.0}}}
        with patch("controlcomparador.comparators.san_isidro.normalizar_pdf", return_value=pdf):
            with patch(
                "controlcomparador.comparators.san_isidro.normalizar_reporte",
                return_value=(rep, set()),
            ):
                coincide, diferencias, avisos = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("DOB" in d and "reporte" in d and "oficial" in d for d in diferencias)
        assert not any("DOB" in a for a in avisos)

    def test_posting_dob_extra_sigue_siendo_error(self):
        pdf = {1: {"caballos": 10, "apuestas": {"GAN": None, "EXA": 2000.0}}}
        posting = ({1: {"EXA": 2000.0, "DOB": 2000.0}}, set())
        coincide, diferencias, avisos = comparar_oficial_con_posting(pdf, posting)
        assert coincide is False
        assert any("DOB" in d and "Posting" in d for d in diferencias)
        assert not any("DOB" in a for a in avisos)

    def test_ter_faltante_en_reporte_es_error(self):
        pdf = {1: {"caballos": 11, "apuestas": {"GAN": None, "SEG": None, "TER": None, "EXA": 2000.0}}}
        rep = {1: {"caballos": 11, "apuestas": {"GAN": None, "SEG": None, "EXA": 2000.0}}}
        with patch("controlcomparador.comparators.san_isidro.normalizar_pdf", return_value=pdf):
            with patch(
                "controlcomparador.comparators.san_isidro.normalizar_reporte",
                return_value=(rep, set()),
            ):
                coincide, diferencias, avisos = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any("TER" in d and "Reporte" in d for d in diferencias)
        assert not any("TER" in a for a in avisos)

    def test_archivos_reales_si_existen(self):
        pdf_path = Path(
            r"c:\Users\cdiaz\Downloads\SI_PROGRAMA_OFICIAL_DEL_12-08-2026_"
            r"(Total_de_carreras_11)_8077.pdf"
        )
        rep_path = Path(r"c:\Users\cdiaz\Downloads\0811_143238_CardRpt.txt")
        if not pdf_path.is_file() or not rep_path.is_file():
            return
        datos_pdf = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(pdf_path))
        datos_rep, _ = normalizar_reporte(rep_path)
        _, diferencias, avisos = comparar_pdf_y_reporte(pdf_path, rep_path)
        assert "EXA" not in datos_pdf[11]["apuestas"]
        if "EXA" in (datos_rep[11].get("apuestas") or {}):
            assert any("Carrera 11" in d and "EXA" in d for d in diferencias)
            assert not any("Carrera 11" in a and "EXA" in a for a in avisos)
        else:
            assert "EXA" in (datos_rep[11].get("bases") or {})
            assert not any("Carrera 11" in d and "EXA" in d for d in diferencias)
