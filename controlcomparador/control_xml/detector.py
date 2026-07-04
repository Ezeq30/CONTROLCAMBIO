# -*- coding: utf-8 -*-

from __future__ import annotations

import xml.etree.ElementTree as ET
from enum import Enum
from pathlib import Path


class TipoXmlHipodromo(str, Enum):
    HSI = "hsi"
    LA_PLATA = "la_plata"


def _desde_nombre(archivo: str) -> TipoXmlHipodromo | None:
    nombre = archivo.upper()
    if "_HSI_" in nombre or nombre.startswith("ARG_HSI"):
        return TipoXmlHipodromo.HSI
    if "_LP_" in nombre or nombre.startswith("ARG_LP"):
        return TipoXmlHipodromo.LA_PLATA
    return None


def _desde_track_ab(track_ab: str) -> TipoXmlHipodromo | None:
    ab = track_ab.strip().upper()
    if ab == "SI":
        return TipoXmlHipodromo.HSI
    if ab == "LP":
        return TipoXmlHipodromo.LA_PLATA
    return None


def _desde_track(track: str) -> TipoXmlHipodromo | None:
    t = track.strip().lower()
    if "san isidro" in t:
        return TipoXmlHipodromo.HSI
    if "la plata" in t:
        return TipoXmlHipodromo.LA_PLATA
    return None


def _peek_meeting_attrs(ruta: Path) -> tuple[str, str]:
    for encoding in ("utf-8", "iso-8859-15", "latin-1"):
        try:
            texto = ruta.read_text(encoding=encoding)
            root = ET.fromstring(texto)
            if root.tag == "Meeting":
                return root.get("trackAb") or "", root.get("track") or ""
        except (ET.ParseError, UnicodeDecodeError, OSError):
            continue
    return "", ""


def detectar_tipo_xml(ruta: str | Path) -> TipoXmlHipodromo:
    path = Path(ruta)
    por_nombre = _desde_nombre(path.name)
    if por_nombre is not None:
        return por_nombre

    track_ab, track = _peek_meeting_attrs(path)
    por_ab = _desde_track_ab(track_ab)
    if por_ab is not None:
        return por_ab
    por_track = _desde_track(track)
    if por_track is not None:
        return por_track

    raise ValueError(
        "XML no reconocido; use un archivo ARG_HSI_* (San Isidro) o ARG_LP_* (La Plata)."
    )
