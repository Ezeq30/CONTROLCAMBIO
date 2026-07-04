# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from controlcomparador.control_xml.detector import TipoXmlHipodromo, detectar_tipo_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "control_xml"


def test_detectar_hsi_por_nombre():
    ruta = FIXTURES / "ARG_HSI_sample.xml"
    assert detectar_tipo_xml(ruta) == TipoXmlHipodromo.HSI


def test_detectar_lp_por_nombre():
    ruta = FIXTURES / "ARG_LP_sample.xml"
    assert detectar_tipo_xml(ruta) == TipoXmlHipodromo.LA_PLATA


def test_detectar_hsi_por_track_ab_sin_prefijo(tmp_path):
    contenido = (FIXTURES / "ARG_HSI_sample.xml").read_text(encoding="utf-8")
    ruta = tmp_path / "reunion.xml"
    ruta.write_text(contenido, encoding="utf-8")
    assert detectar_tipo_xml(ruta) == TipoXmlHipodromo.HSI
