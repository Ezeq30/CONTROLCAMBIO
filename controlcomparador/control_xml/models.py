# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResultadoControlXml:
    hipodromo: str
    fecha: str
    carreras: list[tuple[int, int]]
