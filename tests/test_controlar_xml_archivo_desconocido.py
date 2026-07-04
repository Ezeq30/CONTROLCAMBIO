# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from controlcomparador.control_xml import controlar_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "control_xml"


def test_controlar_xml_archivo_desconocido():
    ruta = FIXTURES / "ARG_UNKNOWN_sample.xml"
    with pytest.raises(ValueError, match="XML no reconocido"):
        controlar_xml(ruta)
