# -*- coding: utf-8 -*-
"""Fecha Palermo: no fusionar 2 reuniones; match PROGRAM DATE con AUG/APR/DEC."""

from pathlib import Path
from unittest.mock import patch

from controlcomparador.agent import AgenteComparacion, _resolver_fecha_palermo
from controlcomparador.comparators.palermo import comparar_palermo
from controlcomparador.parsers.report import extraer_fecha_reporte


def test_extraer_fecha_reporte_aug_ingles(tmp_path: Path):
    ruta = tmp_path / "rep.txt"
    ruta.write_text("PROGRAM DATE: 01-AUG-2026\n", encoding="utf-8")
    assert extraer_fecha_reporte(ruta) == "01/08/2026"


def test_extraer_fecha_reporte_apr_y_dec(tmp_path: Path):
    ruta = tmp_path / "rep.txt"
    ruta.write_text("PROGRAM DATE: 15-APR-26\n", encoding="utf-8")
    assert extraer_fecha_reporte(ruta) == "15/04/2026"
    ruta.write_text("PROGRAM DATE: 3-DEC-2026\n", encoding="utf-8")
    assert extraer_fecha_reporte(ruta) == "03/12/2026"


def test_extraer_fecha_reporte_ago_espanol(tmp_path: Path):
    ruta = tmp_path / "rep.txt"
    ruta.write_text("PROGRAM DATE: 01-AGO-2026\n", encoding="utf-8")
    assert extraer_fecha_reporte(ruta) == "01/08/2026"


def test_resolver_fecha_matchea_reporte():
    fechas = ["1/8/2026", "3/8/2026"]
    with patch("controlcomparador.agent.extraer_fecha_reporte", return_value="01/08/2026"):
        usada, aviso = _resolver_fecha_palermo(fechas, "rep.txt")
    assert usada == "1/8/2026"
    assert aviso is None


def test_resolver_fecha_sin_match_usa_primera_con_aviso():
    fechas = ["1/8/2026", "3/8/2026"]
    with patch("controlcomparador.agent.extraer_fecha_reporte", return_value=None):
        usada, aviso = _resolver_fecha_palermo(fechas, "rep.txt")
    assert usada == "1/8/2026"
    assert aviso is not None
    assert "usando 1/8/2026" in aviso


def test_comparar_palermo_no_fusiona_dob_de_otra_fecha():
    """C9: DOB 1000 el 1/8; DOB 2000 el 3/8. Con fecha 1/8 no debe mezclar."""
    datos_pdf = {
        "fechas": ["1/8/2026", "3/8/2026"],
        "apuestas_por_fecha": {
            "1/8/2026": {
                9: {"EXA": 1000.0, "TRI": 1000.0, "DOB": 1000.0},
                15: {"IMP": 1000.0, "DOB": 2000.0, "CUA": 500.0},
            },
            "3/8/2026": {
                9: {"EXA": 1000.0, "TRI": 1000.0, "DOB": 2000.0},
                15: {"EXA": 1000.0, "DOB": 1000.0},
            },
        },
        "resumen_por_fecha": {
            "1/8/2026": {},
            "3/8/2026": {},
        },
    }
    with patch(
        "controlcomparador.comparators.palermo.normalizar_reporte_palermo",
        return_value=(
            {
                9: {"EXA": 1000.0, "TRI": 1000.0, "DOB": 1000.0},
                15: {"IMP": 1000.0, "DOB": 2000.0, "CUA": 500.0},
            },
            set(),
        ),
    ):
        coincide, diferencias, _, apuestas_pdf, _ = comparar_palermo(
            "pdf", "reporte", fecha_objetivo="1/8/2026", datos_pdf=datos_pdf,
        )
    assert apuestas_pdf[9]["DOB"] == 1000.0
    assert apuestas_pdf[15]["DOB"] == 2000.0
    assert not any("DOB" in d and "difiere" in d for d in diferencias)
    assert diferencias == []
    assert coincide is True


def test_agente_usa_fecha_del_reporte_aug(tmp_path: Path):
    datos_pdf = {
        "fechas": ["1/8/2026", "3/8/2026"],
        "apuestas_por_fecha": {
            "1/8/2026": {9: {"DOB": 1000.0}},
            "3/8/2026": {9: {"DOB": 2000.0}},
        },
        "resumen_por_fecha": {"1/8/2026": {}, "3/8/2026": {}},
    }
    ruta = tmp_path / "rep.txt"
    ruta.write_text("PROGRAM DATE: 01-AUG-2026\n", encoding="utf-8")

    with patch("controlcomparador.agent.leer_palermo_desde_pdf", return_value=datos_pdf):
        with patch(
            "controlcomparador.comparators.palermo.normalizar_reporte_palermo",
            return_value=({9: {"DOB": 1000.0}}, set()),
        ):
            resultado = AgenteComparacion().comparar_palermo("pdf", ruta)

    assert resultado["fecha_usada"] == "1/8/2026"
    assert resultado["datos_pdf"][9]["DOB"] == 1000.0
    assert resultado["coincide"] is True
