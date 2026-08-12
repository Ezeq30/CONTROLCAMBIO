# -*- coding: utf-8 -*-
"""EXA↔IMP / TRI↔CUA: solo control de tela (PDF solo), no en comparación SI vs reporte."""

from unittest.mock import patch

from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte
from controlcomparador.config import MSG_EXA_IMP_JUNTOS, MSG_TRI_CUA_JUNTOS
from controlcomparador.parsers.report import pares_conflictivos, validar_pares_excluyentes
from controlcomparador.ui.tables import _validar_carreras_tela, imprimir_tabla_san_isidro


class TestHelpersPares:
    def test_exa_imp_juntos(self):
        datos = {
            1: {"caballos": 14, "apuestas": {"EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0}},
        }
        errs = validar_pares_excluyentes(datos)
        assert len(errs) == 1
        assert MSG_EXA_IMP_JUNTOS in errs[0]

    def test_tri_cua_juntos(self):
        datos = {2: {"caballos": 10, "apuestas": {"TRI": 2000.0, "CUA": 1000.0}}}
        errs = validar_pares_excluyentes(datos)
        assert any(MSG_TRI_CUA_JUNTOS in e for e in errs)

    def test_exa_tri_permitidos(self):
        datos = {1: {"caballos": 10, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}}}
        assert validar_pares_excluyentes(datos) == []

    def test_imp_cua_permitidos(self):
        datos = {1: {"caballos": 14, "apuestas": {"IMP": 2000.0, "CUA": 1000.0}}}
        assert validar_pares_excluyentes(datos) == []

    def test_pares_conflictivos_mapa(self):
        assert pares_conflictivos({"EXA", "IMP", "TRI"}) == {"EXA": "IMP", "IMP": "EXA"}
        assert pares_conflictivos({"EXA", "TRI"}) == {}


class TestComparacionSiSinPares:
    """ALL EXA/TRI en reporte + IMP/CUA en PDF no debe marcar par en comparación."""

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_all_exa_tri_con_imp_cua_en_pdf_no_marca_par(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {
            1: {
                "caballos": 14,
                "apuestas": {
                    "GAN": None, "SEG": None, "TER": None,
                    "IMP": 2000.0, "CUA": 1000.0, "DOB": 2000.0, "QTN": 2000.0,
                },
            },
        }
        mock_reporte.return_value = ({
            1: {
                "caballos": 14,
                "apuestas": {
                    "GAN": None, "SEG": None, "TER": None,
                    "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0,
                    "DOB": 2000.0, "QTN": 2000.0,
                },
            },
        }, {"EXA", "TRI"})
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert not any(MSG_EXA_IMP_JUNTOS in d for d in diferencias)
        assert not any(MSG_TRI_CUA_JUNTOS in d for d in diferencias)
        assert coincide is False
        assert any("EXA" in d and "Reporte" in d and "PDF" in d for d in diferencias)
        assert any("TRI" in d and "Reporte" in d and "PDF" in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_tabla_si_no_muestra_err_par(self, mock_reporte, mock_pdf):
        pdf = {
            1: {
                "caballos": 14,
                "apuestas": {"IMP": 2000.0, "CUA": 1000.0, "DOB": 2000.0},
            },
        }
        rep = {
            1: {
                "caballos": 14,
                "apuestas": {
                    "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0,
                },
            },
        }
        buf = []
        imprimir_tabla_san_isidro(
            pdf, rep, tipo_pdf="OFICIAL", imprimir=False, par=True, html_buffer=buf,
        )
        estados = [f[-1] for f in buf[0]["filas"]]
        assert not any("≠" in e for e in estados)


class TestControlTelaSigueValidandoPares:
    def test_tela_marca_exa_imp_juntos(self):
        datos = {
            1: {
                "caballos": 14,
                "apuestas": {"IMP": 2000.0, "EXA": 2000.0, "TER": None},
            },
        }
        _, violaciones = _validar_carreras_tela(datos)[1]
        assert any(v[0] == MSG_EXA_IMP_JUNTOS for v in violaciones)

    def test_tela_marca_tri_cua_juntos(self):
        datos = {
            6: {
                "caballos": 11,
                "apuestas": {"EXA": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "TER": None},
            },
        }
        _, violaciones = _validar_carreras_tela(datos)[6]
        assert any(v[0] == MSG_TRI_CUA_JUNTOS for v in violaciones)

    def test_tela_exa_tri_ok(self):
        datos = {
            2: {
                "caballos": 10,
                "apuestas": {"EXA": 2000.0, "TRI": 2000.0, "TER": None},
            },
        }
        _, violaciones = _validar_carreras_tela(datos)[2]
        assert not any(MSG_EXA_IMP_JUNTOS in v[0] for v in violaciones)
        assert not any(MSG_TRI_CUA_JUNTOS in v[0] for v in violaciones)
