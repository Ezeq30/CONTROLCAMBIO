# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from controlcomparador.control_xml.models import ResultadoControlXml
from controlcomparador.control_xml.parsers.base import extraer_resultado, leer_meeting


def parsear(ruta: str | Path) -> ResultadoControlXml:
    path = Path(ruta)
    root = leer_meeting(path, encoding="iso-8859-15")
    return extraer_resultado(root)
