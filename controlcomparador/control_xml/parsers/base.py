# -*- coding: utf-8 -*-

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from controlcomparador.control_xml.models import ResultadoControlXml


def leer_meeting(ruta: Path, *, encoding: str) -> ET.Element:
    texto = ruta.read_text(encoding=encoding)
    return ET.fromstring(texto)


def _formatear_fecha(iso: str) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(iso.strip(), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso


def _numero_carrera(race: ET.Element) -> int:
    raw = race.get("raceNumber")
    if raw and str(raw).strip().isdigit():
        return int(raw)
    nodo = race.find("RaceNumber")
    if nodo is not None and (nodo.text or "").strip().isdigit():
        return int(nodo.text.strip())
    raise ValueError("Carrera sin número válido en el XML")


def _contar_starters(race: ET.Element) -> int:
    starters = race.find("Starters")
    if starters is None:
        return 0
    return len(starters.findall("Starter"))


def extraer_resultado(root: ET.Element) -> ResultadoControlXml:
    hipodromo = (root.get("track") or "").strip() or "Desconocido"
    fecha = _formatear_fecha(root.get("date") or "")
    carreras: list[tuple[int, int]] = []
    races = root.find("Races")
    if races is not None:
        for race in races.findall("Race"):
            carreras.append((_numero_carrera(race), _contar_starters(race)))
    carreras.sort(key=lambda x: x[0])
    return ResultadoControlXml(hipodromo=hipodromo, fecha=fecha, carreras=carreras)
