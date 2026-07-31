# -*- coding: utf-8 -*-
"""EXA↔IMP y TRI↔CUA son excluyentes solo en San Isidro; EXA+TRI e IMP+CUA pueden coexistir."""

from unittest.mock import patch

from controlcomparador.comparators.laplata import comparar_planilla_con_reporte
from controlcomparador.comparators.palermo import comparar_palermo
from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte
from controlcomparador.config import MSG_EXA_IMP_JUNTOS, MSG_TRI_CUA_JUNTOS, SYM_FAIL
from controlcomparador.parsers.report import pares_conflictivos, validar_pares_excluyentes
from controlcomparador.ui.tables import (
    _aplicar_par_excluyente,
    _estado_apuesta,
    _estado_par_excluyente,
    imprimir_tabla_laplata,
    imprimir_tabla_posting_vs_reporte,
    imprimir_tabla_san_isidro,
    imprimir_tablas_palermo,
)


class TestParesExcluyentes:
    def test_exa_imp_juntos_en_reporte(self):
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


class TestCompararConParExcluyente:
    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_exa_de_mas_en_reporte_con_imp_en_tela(self, mock_reporte, mock_pdf):
        """Caso usuario: tela tiene IMP; reporte agrega EXA por error → debe fallar."""
        mock_pdf.return_value = {
            1: {
                "caballos": 14,
                "apuestas": {
                    "GAN": None, "SEG": None, "TER": None,
                    "IMP": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 2000.0,
                },
            },
        }
        mock_reporte.return_value = ({
            1: {
                "caballos": 14,
                "apuestas": {
                    "GAN": None, "SEG": None, "TER": None,
                    "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 2000.0,
                },
            },
        }, set())
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is False
        assert any(MSG_EXA_IMP_JUNTOS in d for d in diferencias)

    @patch("controlcomparador.comparators.san_isidro.normalizar_pdf")
    @patch("controlcomparador.comparators.san_isidro.normalizar_reporte")
    def test_exa_tri_sin_falso_positivo(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {
            1: {"caballos": 10, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}},
        }
        mock_reporte.return_value = ({
            1: {"caballos": 10, "apuestas": {"EXA": 2000.0, "TRI": 2000.0}},
        }, set())
        coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")
        assert coincide is True
        assert diferencias == []


class TestSoloSanIsidro:
    """Palermo/La Plata no deben marcar EXA≠IMP ni TRI≠CUA."""

    @patch("controlcomparador.comparators.palermo.leer_palermo_desde_pdf")
    @patch("controlcomparador.comparators.palermo.normalizar_reporte_palermo")
    def test_palermo_no_valida_pares(self, mock_reporte, mock_pdf):
        mock_pdf.return_value = {
            "fechas": ["01/08/2026"],
            "apuestas_por_fecha": {
                "01/08/2026": {
                    2: {"EXA": 1000.0, "IMP": 1000.0, "TRI": 1000.0, "CUA": 500.0, "DOB": 1000.0},
                },
            },
            "resumen_por_fecha": {},
        }
        mock_reporte.return_value = ({
            2: {"EXA": 1000.0, "IMP": 1000.0, "TRI": 1000.0, "CUA": 500.0, "DOB": 1000.0},
        }, set())
        coincide, diferencias, *_ = comparar_palermo("pdf", "reporte", fecha_objetivo="01/08/2026")
        assert coincide is True
        assert not any(MSG_EXA_IMP_JUNTOS in d for d in diferencias)
        assert not any(MSG_TRI_CUA_JUNTOS in d for d in diferencias)

    @patch("controlcomparador.comparators.laplata.normalizar_planilla_laplata")
    @patch("controlcomparador.comparators.laplata.normalizar_reporte")
    def test_laplata_no_valida_pares(self, mock_reporte, mock_planilla):
        mock_planilla.return_value = {
            1: {"caballos": 14, "apuestas": {"EXA": 500.0, "IMP": 1000.0, "TRI": 500.0, "CUA": 500.0}},
        }
        mock_reporte.return_value = ({
            1: {"caballos": 14, "apuestas": {"EXA": 500.0, "IMP": 1000.0, "TRI": 500.0, "CUA": 500.0}},
        }, set())
        coincide, diferencias = comparar_planilla_con_reporte("xls", "reporte")
        assert coincide is True
        assert not any(MSG_EXA_IMP_JUNTOS in d for d in diferencias)
        assert not any(MSG_TRI_CUA_JUNTOS in d for d in diferencias)

    def test_tabla_palermo_sin_err_par(self):
        bases = {2: {"EXA": 1000.0, "IMP": 1000.0, "TRI": 1000.0, "CUA": 500.0}}
        rep = ({2: {"EXA": 1000.0, "IMP": 1000.0, "TRI": 1000.0, "CUA": 500.0}}, set())
        buf = []
        imprimir_tablas_palermo(bases, rep, ["01/08/2026"], "01/08/2026", imprimir=False, html_buffer=buf)
        estados = [f[-1] for f in buf[0]["filas"]]
        assert not any("≠" in e for e in estados)

    def test_tabla_laplata_sin_err_par(self):
        plan = {1: {"caballos": 14, "apuestas": {"EXA": 500.0, "IMP": 1000.0, "CUA": 500.0}}}
        rep = {1: {"caballos": 14, "apuestas": {"EXA": 500.0, "IMP": 1000.0, "CUA": 500.0}}}
        buf = []
        imprimir_tabla_laplata(plan, rep, imprimir=False, html_buffer=buf)
        estados = [f[-1] for f in buf[0]["filas"]]
        assert not any("≠" in e for e in estados)

    def test_posting_sin_flag_no_marca_par(self):
        posting = ({1: {"EXA": 1000.0, "IMP": 1000.0}}, set())
        reporte = ({1: {"EXA": 1000.0, "IMP": 1000.0}}, set())
        fuente = {1: {"caballos": 14, "apuestas": {"EXA": 1000.0, "IMP": 1000.0}}}
        buf = []
        imprimir_tabla_posting_vs_reporte(
            posting, reporte, html_buffer=buf, datos_fuente=fuente,
            label_fuente="Bases Palermo", imprimir=False, validar_pares=False,
        )
        estados = [f[-1] for f in buf[0]["filas"]]
        assert not any("≠" in e for e in estados)

    def test_posting_con_flag_si_marca_par(self):
        posting = ({1: {"EXA": 1000.0, "IMP": 1000.0}}, set())
        reporte = ({1: {"EXA": 1000.0, "IMP": 1000.0}}, set())
        fuente = {1: {"caballos": 14, "apuestas": {"EXA": 1000.0, "IMP": 1000.0}}}
        buf = []
        imprimir_tabla_posting_vs_reporte(
            posting, reporte, html_buffer=buf, datos_fuente=fuente,
            label_fuente="TELA OFICIAL", imprimir=False, validar_pares=True,
        )
        estados = [f[-1] for f in buf[0]["filas"]]
        assert any("≠" in e for e in estados)


class TestEstadoTablaParExcluyente:
    def test_no_tela_se_eleva_a_error_si_hay_imp(self):
        estado = _estado_apuesta(None, 2000.0, "TELA OFICIAL", "reporte")
        assert "no" in estado.lower()
        estado = _aplicar_par_excluyente(estado, "EXA", {"EXA": "IMP", "IMP": "EXA"})
        assert SYM_FAIL in estado
        assert "≠IMP" in estado

    def test_estado_corto_cabe_en_columna_par(self):
        assert len(_estado_par_excluyente("IMP").replace("[red]", "").replace("[/red]", "")) <= 13

    def test_tabla_marca_error_en_exa(self):
        pdf = {
            1: {
                "caballos": 14,
                "apuestas": {"IMP": 2000.0, "TRI": 2000.0, "DOB": 2000.0},
            },
        }
        rep = {
            1: {
                "caballos": 14,
                "apuestas": {
                    "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "DOB": 2000.0,
                },
            },
        }
        bloque = imprimir_tabla_san_isidro(
            pdf, rep, tipo_pdf="TELA OFICIAL", imprimir=False, par=True,
        )
        assert bloque.num_errores >= 2
        buf = []
        imprimir_tabla_san_isidro(
            pdf, rep, tipo_pdf="TELA OFICIAL", imprimir=False, par=True, html_buffer=buf,
        )
        assert buf
        planos = []
        for fila in buf[0]["filas"]:
            if fila[2] in ("EXA", "IMP"):
                planos.append(fila[-1])
        assert any("≠IMP" in p or SYM_FAIL in p for p in planos)
        assert any("≠EXA" in p or SYM_FAIL in p for p in planos)
