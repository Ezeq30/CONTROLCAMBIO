# -*- coding: utf-8 -*-

from pathlib import Path

from controlcomparador.control_xml import controlar_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "control_xml"


def test_parser_hsi_fixture():
    ruta = FIXTURES / "ARG_HSI_sample.xml"
    resultado = controlar_xml(ruta)
    assert resultado.hipodromo == "Hipódromo de San Isidro"
    assert resultado.fecha == "03/07/2026"
    assert resultado.carreras == [(1, 3), (2, 2)]


def test_parser_hsi_archivo_real_si_existe():
    ruta = Path(r"c:\Users\cdiaz\Downloads\ARG_HSI_20260703.xml")
    if not ruta.is_file():
        return
    resultado = controlar_xml(ruta)
    assert len(resultado.carreras) == 11
    assert all(cab > 0 for _, cab in resultado.carreras)
