# -*- coding: utf-8 -*-
"""Avisos cuando reporte/posting tienen apuestas que la tela no tiene."""

from pathlib import Path
from unittest.mock import patch

from controlcomparador.comparators.posting import comparar_oficial_con_posting
from controlcomparador.comparators.san_isidro import comparar_pdf_y_reporte
from controlcomparador.parsers.pdf import (
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)
from controlcomparador.parsers.report import normalizar_reporte


def _base_apuestas():
    return {"GAN": None, "SEG": None, "TER": None, "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0}


class TestApuestasExtraSinTela:
    def test_c4_c7_c11_reporte_all_exa_tri(self):
        """C4/C7/C11 sin EXA/TRI en tela pero con ALL en reporte → aviso por carrera."""
        pdf = {}
        for n in range(1, 12):
            ap = _base_apuestas().copy()
            if n == 4:
                ap = {k: v for k, v in ap.items() if k not in ("EXA", "TRI")}
                ap["IMP"] = 2000.0
                ap["QTN"] = 1000.0
                ap["CUA"] = 1000.0
            elif n == 5:
                ap["TPL"] = 2000.0
            elif n == 7:
                ap = {k: v for k, v in ap.items() if k != "TRI"}
                ap["QTP"] = 1000.0
                ap["CUA"] = 1000.0
            elif n == 9:
                ap["TPL"] = 5000.0
            elif n == 11:
                ap = {k: v for k, v in ap.items() if k not in ("EXA", "TRI")}
                ap["IMP"] = 5000.0
                ap["CUA"] = 2000.0
            pdf[n] = {"caballos": 10, "apuestas": ap}

        rep = {}
        for n in range(1, 12):
            rep[n] = {"caballos": 10, "apuestas": _base_apuestas().copy()}
            if n == 2:
                rep[n]["apuestas"]["CAD"] = 200.0
            elif n == 3:
                rep[n]["apuestas"]["QTN"] = 500.0
            elif n == 4:
                rep[n]["apuestas"].update({"IMP": 2000.0, "QTN": 1000.0, "CUA": 1000.0})
            elif n == 5:
                rep[n]["apuestas"]["TPL"] = 2000.0
            elif n == 6:
                rep[n]["apuestas"]["QTN"] = 2000.0
            elif n == 7:
                rep[n]["apuestas"].update({"QTP": 1000.0, "CUA": 1000.0})
            elif n == 8:
                rep[n]["apuestas"]["QTN"] = 2000.0
            elif n == 10:
                rep[n]["apuestas"]["DOB"] = 5000.0
            elif n == 11:
                rep[n]["apuestas"].update({"IMP": 5000.0, "CUA": 2000.0})

        with patch("controlcomparador.comparators.san_isidro.normalizar_pdf", return_value=pdf):
            with patch(
                "controlcomparador.comparators.san_isidro.normalizar_reporte",
                return_value=(rep, {"EXA", "TRI"}),
            ):
                coincide, diferencias = comparar_pdf_y_reporte("pdf", "reporte")

        assert coincide is False
        c4 = next(d for d in diferencias if d.startswith("Carrera 4:") and "Reporte" in d)
        assert "EXA" in c4 and "TRI" in c4
        c7 = next(d for d in diferencias if d.startswith("Carrera 7:") and "Reporte" in d)
        assert "TRI" in c7
        c11 = next(d for d in diferencias if d.startswith("Carrera 11:") and "Reporte" in d)
        assert "EXA" in c11 and "TRI" in c11

    def test_posting_exa_sin_tela_c4(self):
        pdf = {
            4: {
                "caballos": 12,
                "apuestas": {"GAN": None, "IMP": 2000.0, "DOB": 2000.0},
            },
        }
        posting = ({4: {"EXA": 2000.0, "TRI": 2000.0, "IMP": 2000.0, "DOB": 2000.0}}, {"EXA", "TRI"})
        coincide, diferencias = comparar_oficial_con_posting(pdf, posting)
        assert coincide is False
        assert any("Carrera 4" in d and "EXA" in d and "Posting" in d for d in diferencias)
        assert any("Carrera 4" in d and "TRI" in d and "Posting" in d for d in diferencias)

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
        _, diferencias = comparar_pdf_y_reporte(pdf_path, rep_path)
        extras = [d for d in diferencias if "presentes en Reporte pero no en PDF" in d]
        assert any("Carrera 4" in d and "EXA" in d for d in extras)
        assert any("Carrera 11" in d and "EXA" in d for d in extras)
        assert "EXA" not in datos_pdf[11]["apuestas"]
        assert "EXA" in datos_rep[11]["apuestas"]
