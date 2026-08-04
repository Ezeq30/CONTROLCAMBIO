# -*- coding: utf-8 -*-
"""Fecha/reunión de tela: título Programa Depurado, no fechas del cuerpo."""

from controlcomparador.parsers.pdf import _parsear_info_reunion_tela, extraer_info_reunion_tela


_TEXTO_PAGINA1_REALISTA = """\
Pagina      1 
Programa Depurado Reunion 71 del 08/08/2026
Jockey Club
Hipodromo de San Isidro
TOTAL EN POZOS: $ 165.000.000.-
Premio KETAMINA 2016 (REABIERTA )
Condicion: Potrancas 3 anos
APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000
primeros puestos en la estadistica por sumas ganadas desde el 01/08/2025
"""


class TestParsearInfoReunionTela:
    def test_titulo_gana_sobre_fecha_cuerpo(self):
        info = _parsear_info_reunion_tela(_TEXTO_PAGINA1_REALISTA)
        assert info["reunion"] == "71"
        assert info["fecha"] == "08/08/2026"
        assert info["hipodromo"] == "Hipodromo de San Isidro"

    def test_titulo_partido_en_lineas(self):
        texto = (
            "Programa Depurado Reunion 71\n"
            "del 08/08/2026\n"
            "Hipodromo de San Isidro\n"
            "Premio X\n"
            "desde el 01/08/2025\n"
        )
        info = _parsear_info_reunion_tela(texto)
        assert info["reunion"] == "71"
        assert info["fecha"] == "08/08/2026"

    def test_fallback_encabezado_sin_titulo_completo(self):
        texto = (
            "Reunion 54\n"
            "14/06/2026\n"
            "Hipodromo de San Isidro\n"
            "Premio FOO\n"
            "01/01/2020\n"
        )
        info = _parsear_info_reunion_tela(texto)
        assert info["reunion"] == "54"
        assert info["fecha"] == "14/06/2026"


def test_extraer_info_reunion_pdf_real():
    from pathlib import Path

    pdf = Path(r"c:\Users\cdiaz\Downloads\SI PROGRAMA OFICIAL 08-08-2026.pdf")
    if not pdf.is_file():
        return
    info = extraer_info_reunion_tela(pdf)
    assert info["reunion"] == "71"
    assert info["fecha"] == "08/08/2026"
    assert "San Isidro" in info["hipodromo"]
