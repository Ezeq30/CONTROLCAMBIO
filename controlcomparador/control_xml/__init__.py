# -*- coding: utf-8 -*-

from controlcomparador.control_xml.models import ResultadoControlXml
from controlcomparador.control_xml.detector import TipoXmlHipodromo, detectar_tipo_xml
from controlcomparador.control_xml.ui import controlar_xml, imprimir_control_xml

__all__ = [
    "ResultadoControlXml",
    "TipoXmlHipodromo",
    "detectar_tipo_xml",
    "controlar_xml",
    "imprimir_control_xml",
]
