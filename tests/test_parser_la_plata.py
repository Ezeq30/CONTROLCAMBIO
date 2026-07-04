# -*- coding: utf-8 -*-

from pathlib import Path

from controlcomparador.control_xml import controlar_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "control_xml"


def test_parser_la_plata_fixture():
    ruta = FIXTURES / "ARG_LP_sample.xml"
    resultado = controlar_xml(ruta)
    assert resultado.hipodromo == "Hipodromo de La Plata"
    assert resultado.fecha == "05/07/2026"
    assert resultado.carreras == [(1, 4), (2, 2)]


def test_parser_la_plata_archivo_real_si_existe():
    ruta = Path(r"c:\Users\cdiaz\Downloads\ARG_LP_20260705.xml")
    if not ruta.is_file():
        return
    resultado = controlar_xml(ruta)
    assert len(resultado.carreras) == 9
    assert all(cab > 0 for _, cab in resultado.carreras)
