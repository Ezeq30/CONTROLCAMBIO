# -*- coding: utf-8 -*-
"""Regresión: tabla La Plata lee montos Rep. desde bases (RSM), no apuestas (pools)."""

from controlcomparador.parsers.report import normalizar_reporte
from controlcomparador.ui import tables


def _planilla_y_reporte_split():
    """Formato CardRpt post-refactor SI/LP: apuestas=None (pools), bases=montos."""
    plan = {
        1: {"caballos": 8, "apuestas": {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 500.0}},
        2: {"caballos": 8, "apuestas": {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "CAD": 500.0}},
    }
    rep = {
        1: {
            "caballos": 8,
            "apuestas": {
                "GAN": None, "SEG": None, "EXA": None, "TRI": None, "DOB": None, "QTN": None,
            },
            "bases": {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 500.0},
        },
        2: {
            "caballos": 8,
            "apuestas": {
                "GAN": None, "SEG": None, "EXA": None, "TRI": None, "DOB": None, "CAD": None,
            },
            "bases": {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "CAD": 500.0},
        },
    }
    return plan, rep


def _filas_html(bloque_fn):
    html_buffer: list = []
    bloque_fn(html_buffer)
    assert html_buffer, "debe registrar sección HTML"
    return html_buffer[0]["filas"]


def test_laplata_tabla_izq_montos_desde_bases_par():
    plan, rep = _planilla_y_reporte_split()
    bloque = tables.imprimir_tabla_laplata(plan, rep, imprimir=False, par=True)
    assert bloque.num_errores == 0

    filas = _filas_html(
        lambda buf: tables.imprimir_tabla_laplata(
            plan, rep, html_buffer=buf, imprimir=False, par=True,
        )
    )
    exa_c1 = next(f for f in filas if f[0] == "1" and f[2] == "EXA")
    assert exa_c1[3] == "500", "Planilla"
    assert exa_c1[4] == "500", "Rep. debe venir de bases, no de apuestas None"


def test_laplata_tabla_izq_montos_desde_bases_sin_par():
    plan, rep = _planilla_y_reporte_split()
    bloque = tables.imprimir_tabla_laplata(plan, rep, imprimir=False, par=False)

    filas = _filas_html(
        lambda buf: tables.imprimir_tabla_laplata(
            plan, rep, html_buffer=buf, imprimir=False, par=False,
        )
    )
    cad_c2 = next(f for f in filas if f[2] == "CAD")
    assert cad_c2[3] == "500"
    assert cad_c2[4] == "500"


def test_laplata_fixture_normalizar_reporte_no_rep_vacio(ruta_reporte_laplata):
    datos_rep, _ = normalizar_reporte(ruta_reporte_laplata)
    plan = {
        n: {
            "caballos": d["caballos"],
            "apuestas": dict(d.get("bases") or {}),
        }
        for n, d in datos_rep.items()
    }
    bloque = tables.imprimir_tabla_laplata(plan, datos_rep, imprimir=False, par=True)
    assert bloque.num_errores == 0

    filas = _filas_html(
        lambda buf: tables.imprimir_tabla_laplata(
            plan, datos_rep, html_buffer=buf, imprimir=False, par=True,
        )
    )
    reps = [f[4] for f in filas if f[4] != "-"]
    assert reps, "Rep. no debe quedar todo en '-' con fixture reporte_laplata"
