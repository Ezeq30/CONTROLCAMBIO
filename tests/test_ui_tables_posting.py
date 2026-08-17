# -*- coding: utf-8 -*-
"""Tests de vista par en consola (posting lado a lado, San Isidro/Palermo/La Plata)."""

import re

from rich import box

from controlcomparador.ui import tables
from controlcomparador.ui.console import console


def _assert_salida_par_compacta(salida: str, *, min_lineas: int = 5) -> int:
    """Checks comunes vista par; retorna max ancho de línea."""
    assert not re.search(r"╯\s{3,}╭", salida)
    assert not re.search(r"┘\s{3,}┌", salida)
    assert not re.search(r"╭[^\n]*╮[^\n]*│\s*╭", salida)
    assert "[38;2;" not in salida
    assert "Segment(" not in salida
    assert "Style(color=" not in salida
    assert "ColorTriplet" not in salida
    lineas = salida.splitlines()
    assert len(lineas) >= min_lineas
    ancho = max(len(l) for l in lineas)
    assert ancho <= 145
    return ancho


def test_perfil_columnas_con_posting():
    cols = tables._perfil_columnas_comparacion(
        "TELA OFICIAL", con_posting=True, compacto=True, par=True,
    )
    nombres = [c[0] for c in cols]
    assert nombres == [
        "Carr.", "Cab.", "Ap.", "Tela Oficial", "Rep.", "Post.", "Estado",
    ]


def test_perfil_columnas_posting_rsm_table():
    cols = tables._perfil_columnas_comparacion(
        "OFICIAL", con_posting=True, compacto=True, par=True,
        etiqueta_apuesta=tables._header_columna_rsm(par=True),
    )
    nombres = [c[0] for c in cols]
    assert nombres[2] == "RSM"
    assert "Ap." not in nombres


def test_perfil_columnas_con_ap_rep():
    cols = tables._perfil_columnas_comparacion(
        "OFICIAL", con_posting=False, compacto=True, par=True, con_ap_rep=True,
    )
    nombres = [c[0] for c in cols]
    assert nombres == [
        "Carr.", "Cab.", "Ap.", "Ap.R", "Oficial", "Rep.", "Estado",
    ]


def test_perfil_columnas_si_bases_rsm():
    cols = tables._perfil_columnas_comparacion(
        "OFICIAL", con_posting=False, compacto=True, par=True,
        con_ap_rep=True, bases_rsm=True,
    )
    nombres = [c[0] for c in cols]
    assert nombres == [
        "Carr.", "Cab.", "Ap.", "Ap.R", "Oficial", "B.RSM", "Estado",
    ]
    assert tables._header_columna_reporte(par=False, bases_rsm=True) == "BASES RSM TABLE"


def test_caballos_par_no_trunca():
    kw = tables._kwargs_col_caballos(par=True)
    assert kw["width"] >= 5
    assert kw["min_width"] == 5


def test_caballos_celda_roja_si_difieren():
    assert "[fail]" in tables._caballos_celda_rich(8, 7)
    assert "8/7" in tables._caballos_celda_rich(8, 7)
    assert "[fail]" not in tables._caballos_celda_rich(8, 8)
    assert tables._caballos_celda_rich_texto("8/7").startswith("[fail]")
    assert tables._caballos_celda_rich_texto("8/8") == "8/8"


def test_headers_completos_par():
    assert tables._header_columna_fuente("TELA OFICIAL", par=True) == "Tela Oficial"
    assert tables._header_columna_reporte(par=True) == "Rep."
    assert tables._header_columna_reporte(par=True, bases_rsm=True) == "B.RSM"
    assert tables._header_columna_rsm(par=True) == "RSM"
    assert tables._header_columna_rsm(par=False) == "RSM Table"
    assert tables._header_columna_posting(par=True) == "Post."


def test_ancho_valor_par():
    assert tables._ancho_valor(par=True) == 6


def test_tabla_par_usa_rounded():
    cols = tables._perfil_columnas_comparacion(
        "OFICIAL", con_posting=True, par=True,
    )
    t = tables._crear_tabla_comparacion(cols, par=True)
    assert t.box == box.ROUNDED


def test_titulos_panel_par():
    assert tables._titulo_panel_izq("COMPARACION TELA OFICIAL vs REPORTE") == "TELA OFICIAL vs Reporte"
    titulo_der = "COMPARACION TELA OFICIAL · POSTING · REPORTE"
    assert tables._titulo_panel_der(titulo_der) == "Posting Vs Tela Oficial vs Reporte"


def test_titulos_panel_par_palermo():
    assert tables._titulo_panel_izq("COMPARACION BASES PALERMO vs REPORTE") == "BASES PALERMO vs Reporte"
    titulo_der = "COMPARACION Bases Palermo · POSTING · REPORTE"
    assert tables._titulo_panel_der(titulo_der) == "Posting Vs Bases Palermo vs Reporte"


def test_escribir_salida_fija_preserva_ancho():
    import io
    import sys
    from controlcomparador.ui.console import escribir_salida_fija

    linea = "A" * 58 + "B" * 67
    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        escribir_salida_fija(linea + "\n")
    finally:
        sys.stdout = old
    out = cap.getvalue().splitlines()[0]
    assert len(out) == 125


def _capturar_salida_par(fn) -> str:
    """Captura stdout (escritura directa de paneles pegados)."""
    import io
    import sys

    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        fn()
    finally:
        sys.stdout = old
    return cap.getvalue()


def test_imprimir_par_palermo_misma_altura_secciones():
    datos_bases = {
        1: {"EXA": 1000.0, "QTN": 500.0},
        2: {"EXA": 1000.0},
    }
    datos_rep = ({1: {"EXA": 1000.0}, 2: {"EXA": 1000.0, "QTN": 500.0}}, set())
    posting = ({1: {"EXA": 1000.0, "QTN": 500.0}, 2: {"EXA": 1000.0}}, set())
    bloque_izq = tables.imprimir_tablas_palermo(
        datos_bases, datos_rep, ["4/7/2026"], "4/7/2026", posting,
        imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, datos_rep,
        datos_fuente=datos_bases,
        label_fuente="Bases Palermo",
        imprimir=False, compacto=True, par=True,
    )
    cols_izq = [c.header for c in bloque_izq.tabla.columns]
    assert "Post." not in cols_izq
    console.width = 160
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    assert "BASES PALERMO vs Reporte" in salida
    assert "Bases" in salida
    assert "Rep." in salida or "Reporte" in salida
    cols_der = [c.header for c in bloque_der.tabla.columns]
    assert "Post." in cols_der
    assert bloque_izq.subtitulo is not None
    assert "Fechas detectadas" in bloque_izq.subtitulo
    _assert_salida_par_compacta(salida, min_lineas=10)


def test_imprimir_par_muestra_ambas_tablas():
    datos_pdf = {
        1: {"caballos": 11, "apuestas": {"GAN": None, "EXA": 2000}},
    }
    datos_rep_meta = {
        1: {"caballos": 11, "apuestas": {"GAN": None, "EXA": 2000}},
    }
    datos_rep_flat = {1: {"GAN": None, "EXA": 2000}}
    posting = ({1: {"GAN": None, "EXA": 2000}}, set())
    bloque_izq = tables.imprimir_tabla_san_isidro(
        datos_pdf, datos_rep_meta, posting,
        tipo_pdf="OFICIAL", imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, (datos_rep_flat, set()),
        datos_fuente=datos_pdf,
        datos_reporte_meta=datos_rep_meta,
        label_fuente="OFICIAL",
        imprimir=False, compacto=True, par=True,
    )
    console.width = 160
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    assert "OFICIAL vs Reporte" in salida
    assert "Oficial" in salida
    assert "B.RSM" in salida or "Rep." in salida or "Reporte" in salida
    cols_izq = [c.header for c in bloque_izq.tabla.columns]
    assert "Post." not in cols_izq
    assert "Ap.R" in cols_izq
    cols_der = [c.header for c in bloque_der.tabla.columns]
    assert "Post." in cols_der
    assert "RSM" in cols_der
    _assert_salida_par_compacta(salida)


def test_imprimir_par_san_isidro_tela_12_carreras_compacto():
    datos_pdf = {
        i: {"caballos": 10, "apuestas": {"GAN": None, "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0}}
        for i in range(1, 13)
    }
    datos_rep_meta = dict(datos_pdf)
    datos_rep_flat = {i: d["apuestas"] for i, d in datos_pdf.items()}
    posting = ({i: d["apuestas"] for i, d in datos_pdf.items()}, set())
    bloque_izq = tables.imprimir_tabla_san_isidro(
        datos_pdf, datos_rep_meta, posting,
        fecha_reporte="12/07/2026", tipo_pdf="TELA OFICIAL",
        imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, (datos_rep_flat, set()),
        datos_fuente=datos_pdf,
        datos_reporte_meta=datos_rep_meta,
        label_fuente="TELA OFICIAL",
        imprimir=False, compacto=True, par=True,
    )
    cols_izq = [c.header for c in bloque_izq.tabla.columns]
    assert "Post." not in cols_izq
    assert "Ap.R" in cols_izq
    assert "B.RSM" in cols_izq
    cols_der = [c.header for c in bloque_der.tabla.columns]
    assert "Post." in cols_der
    assert "RSM" in cols_der
    assert "B.RSM" in cols_der
    console.width = 200
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=40)
    assert ancho <= 145
    assert "\u2026" not in salida
    assert "TELA OFICIAL vs Reporte" in salida
    assert "│  12  " in salida or "│ 12   " in salida or " 12 " in salida


def test_imprimir_par_palermo_14_carreras_compacto():
    datos_bases = {i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}
    datos_rep = ({i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}, set())
    posting = ({i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}, set())
    bloque_izq = tables.imprimir_tablas_palermo(
        datos_bases, datos_rep, ["4/7/2026"], "4/7/2026", posting,
        imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, datos_rep,
        datos_fuente=datos_bases,
        label_fuente="Bases Palermo",
        imprimir=False, compacto=True, par=True,
    )
    console.width = 200
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=40)
    assert ancho <= 130
    assert "\u2026" not in salida
    assert "│ EXA " in salida or "│ EXA │" in salida or " EXA " in salida
    assert "│  14  " in salida or "│ 14   " in salida or " 14 " in salida


def test_par_no_expande_con_consola_ancha():
    """Consola ancha no debe inflar tablas ni crear hueco entre paneles."""
    datos_bases = {i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}
    datos_rep = ({i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}, set())
    posting = ({i: {"EXA": 1000.0, "TRI": 1000.0} for i in range(1, 15)}, set())
    console.width = 400
    bloque_izq = tables.imprimir_tablas_palermo(
        datos_bases, datos_rep, ["4/7/2026"], "4/7/2026", posting,
        imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, datos_rep, datos_fuente=datos_bases, label_fuente="Bases Palermo",
        imprimir=False, compacto=True, par=True,
    )
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=40)
    assert ancho <= 130
    assert "\u2026" not in salida
    assert "│ EXA " in salida or "│ EXA │" in salida or " EXA " in salida


def test_imprimir_par_laplata_sin_gan_y_sin_post_izq():
    plan = {
        1: {"caballos": 5, "apuestas": {"GAN": None, "EXA": 500.0, "TRI": 500.0, "DOB": 1000.0}},
        6: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 2000.0}},
    }
    rep = {
        1: {"caballos": 5, "apuestas": {"GAN": None, "EXA": 500.0, "TRI": 500.0, "DOB": 1000.0}},
        6: {"caballos": 9, "apuestas": {"GAN": None, "SEG": None, "EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 2000.0}},
    }
    posting = ({1: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0}, 6: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 2000.0}}, set())
    bloque_izq = tables.imprimir_tabla_laplata(
        plan, rep, posting, imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, ({1: rep[1]["apuestas"], 6: rep[6]["apuestas"]}, set()),
        datos_fuente=plan, datos_reporte_meta=rep, label_fuente="Planilla",
        imprimir=False, compacto=True, par=True,
    )
    cols_izq = [c.header for c in bloque_izq.tabla.columns]
    assert "Post." not in cols_izq
    assert len(bloque_izq.tabla.rows) == len(bloque_der.tabla.rows)
    console.width = 400
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=8)
    assert ancho <= 130
    assert "GAN" not in salida
    assert "\u2026" not in salida
    assert not re.search(r"╯\s{3,}╭", salida)
    assert not re.search(r"╮\s{3,}╭", salida)


def _mock_laplata_9_carreras():
    """Datos similares al paste real La Plata + posting."""
    ap = {
        1: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 500.0},
        2: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "CAD": 500.0},
        3: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 1000.0},
        4: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "TPL": 1000.0},
        5: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTP": 500.0},
        6: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "QTN": 2000.0},
        7: {"EXA": 500.0, "TRI": 500.0, "DOB": 1000.0, "TPL": 2000.0},
        8: {"EXA": 500.0, "TRI": 500.0, "DOB": 2000.0},
        9: {"IMP": 1000.0, "CUA": 500.0},
    }
    cab = {1: 5, 2: 5, 3: 6, 4: 7, 5: 6, 6: 9, 7: 12, 8: 9, 9: 14}
    plan, rep, post = {}, {}, {}
    for n, bets in ap.items():
        c = cab[n]
        plan[n] = {"caballos": c, "apuestas": dict(bets, GAN=None)}
        rep[n] = {"caballos": c, "apuestas": dict(bets, GAN=None, SEG=None, TER=None)}
        post[n] = {k: v for k, v in bets.items() if v is not None}
    return plan, rep, post


def test_imprimir_par_laplata_9_carreras_alineadas():
    plan, rep, post = _mock_laplata_9_carreras()
    posting = (post, set())
    rep_flat = {n: d["apuestas"] for n, d in rep.items()}
    bloque_izq = tables.imprimir_tabla_laplata(
        plan, rep, posting, imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, (rep_flat, set()),
        datos_fuente=plan, datos_reporte_meta=rep, label_fuente="Planilla",
        imprimir=False, compacto=True, par=True,
    )
    assert len(bloque_izq.tabla.rows) == len(bloque_der.tabla.rows)
    console.width = 400
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=30)
    assert ancho <= 130
    assert "\u2026" not in salida
    assert not re.search(r"╯\s{3,}╭", salida)
    assert not re.search(r"╮\s{3,}╭", salida)
    lineas = [l for l in salida.splitlines() if "│" in l and "Carr." not in l]
    anchos = {len(l) for l in lineas if l.strip()}
    assert len(anchos) <= 2
    for n in (3, 5, 9):
        filas_n = [l for l in lineas if f"│  {n}   │" in l or f"│ {n}   │" in l]
        assert filas_n, f"carrera {n} debe aparecer en salida"
        for ln in filas_n:
            assert ln.count(f"│  {n}   │") + ln.count(f"│ {n}   │") >= 2, (
                f"carrera {n} debe estar en ambas tablas misma línea"
            )


def test_titulo_par_centrado_en_ancho():
    t = tables._titulo_par_texto("PLANILLA vs Reporte - LA PLATA", 57)
    plain = t.plain
    assert len(plain) == 57
    assert plain.strip() == "PLANILLA vs Reporte - LA PLATA"
    assert plain.index("PLANILLA") > 0
    assert plain.rindex("PLATA") < 56


def test_imprimir_par_titulos_centrados_sobre_tablas():
    plan, rep, post = _mock_laplata_9_carreras()
    posting = (post, set())
    bloque_izq = tables.imprimir_tabla_laplata(
        plan, rep, posting, imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, ({n: d["apuestas"] for n, d in rep.items()}, set()),
        datos_fuente=plan, datos_reporte_meta=rep, label_fuente="Planilla",
        imprimir=False, compacto=True, par=True,
    )
    _, _, _, _, _, ai, ad = tables._preparar_par_sin_panel(bloque_izq, bloque_der)
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    titulo = salida.splitlines()[0]
    assert len(titulo) == ai + ad
    izq_txt = "PLANILLA vs Reporte - LA PLATA"
    der_txt = "Posting Vs Planilla vs Reporte"
    assert titulo[:ai].strip() == izq_txt
    assert titulo[ai:].strip() == der_txt
    assert titulo[:ai] == izq_txt.center(ai)
    assert titulo[ai:] == der_txt.center(ad)


def test_imprimir_par_laplata_no_planilla_sin_hueco():
    """Carrera 9 con EXA/TRI solo en reporte no debe inflar ancho ni dejar hueco."""
    plan, rep, post = _mock_laplata_9_carreras()
    rep[9]["apuestas"]["EXA"] = 500.0
    rep[9]["apuestas"]["TRI"] = 500.0
    post[9]["EXA"] = 500.0
    post[9]["TRI"] = 500.0
    plan[9]["apuestas"] = {"IMP": 1000.0, "CUA": 500.0, "GAN": None}
    posting = (post, set())
    bloque_izq = tables.imprimir_tabla_laplata(
        plan, rep, posting, imprimir=False, compacto=True, par=True,
    )
    bloque_der = tables.imprimir_tabla_posting_vs_reporte(
        posting, ({n: d["apuestas"] for n, d in rep.items()}, set()),
        datos_fuente=plan, datos_reporte_meta=rep, label_fuente="Planilla",
        imprimir=False, compacto=True, par=True,
    )
    _, _, _, _, _, ai, ad = tables._preparar_par_sin_panel(bloque_izq, bloque_der)
    assert ai <= 60, f"tabla izq demasiado ancha ({ai})"
    assert ad <= 72, f"tabla der demasiado ancha ({ad})"
    console.width = 400
    salida = _capturar_salida_par(
        lambda: tables.imprimir_par_comparacion(bloque_izq, bloque_der)
    )
    ancho = _assert_salida_par_compacta(salida, min_lineas=30)
    assert ancho <= 130
    assert (
        "no planilla" in salida
        or "no en planil" in salida
        or "extra" in salida
        or "≠IMP" in salida
        or "≠CUA" in salida
        or "[ERR]" in salida
    )
    assert not re.search(r"╮\s{3,}╭", salida)
    assert not re.search(r"╯\s{3,}╭", salida)
    for ln in salida.splitlines():
        if "Carr." in ln or not ln.strip():
            continue
        plain = re.sub(r"\x1b\[[0-9;]*m", "", ln)
        m = re.search(r"(\||\u2502)\s{3,}(\||\u2502)", plain)
        if m and plain.index(m.group(0)) > len(plain) // 3:
            # hueco entre tablas (no separadores internos de celdas)
            assert len(m.group(2)) <= 2, f"hueco entre tablas: {repr(plain[max(0, m.start()-5):m.end()+5])}"
