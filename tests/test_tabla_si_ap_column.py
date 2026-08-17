# -*- coding: utf-8 -*-
"""Columna Ap. en tabla SI: solo apuestas del PDF, no del reporte."""

from pathlib import Path

from controlcomparador.parsers.pdf import (
    es_tela_oficial,
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)
from controlcomparador.parsers.report import normalizar_reporte
from controlcomparador.ui.tables import imprimir_tabla_san_isidro


def _codigos_ap_por_carrera(html_buffer: list) -> dict[int, list[str]]:
    """Extrae códigos Ap. agrupados por carrera desde html_buffer."""
    por_carrera: dict[int, list[str]] = {}
    carrera_actual = None
    for fila in html_buffer[0]["filas"]:
        if fila[0]:
            carrera_actual = int(fila[0])
            por_carrera.setdefault(carrera_actual, [])
        if carrera_actual is not None and fila[2] != "-":
            por_carrera[carrera_actual].append(fila[2])
    return por_carrera


class TestColumnaApSoloPdf:
    def test_c11_sin_exa_tri_si_no_estan_en_tela(self):
        """Reporte con ALL EXA/TRI no debe agregar filas Ap. si la tela no las tiene."""
        pdf = {
            11: {
                "caballos": 15,
                "apuestas": {
                    "GAN": None,
                    "SEG": None,
                    "TER": None,
                    "IMP": 2000.0,
                    "CUA": 2000.0,
                },
            },
        }
        rep = {
            11: {
                "caballos": 15,
                "apuestas": {
                    "GAN": None,
                    "SEG": None,
                    "TER": None,
                    "EXA": 2000.0,
                    "IMP": 2000.0,
                    "TRI": 2000.0,
                    "CUA": 2000.0,
                },
            },
        }
        buf: list = []
        imprimir_tabla_san_isidro(
            pdf, rep, tipo_pdf="TELA OFICIAL", imprimir=False, html_buffer=buf,
        )
        codigos = _codigos_ap_por_carrera(buf)[11]
        assert codigos == ["GAN", "SEG", "TER", "IMP", "CUA"]
        assert "EXA" not in codigos
        assert "TRI" not in codigos
        apr = []
        carrera_actual = None
        for fila in buf[0]["filas"]:
            if fila[0]:
                carrera_actual = int(fila[0])
            if carrera_actual == 11 and fila[3] != "-":
                apr.append(fila[3])
        assert "EXA" in apr
        assert "TRI" in apr

    def test_archivos_reales_c11_si_existen(self):
        pdf_path = Path(
            r"c:\Users\cdiaz\Downloads\SI_PROGRAMA_OFICIAL_DEL_12-08-2026_"
            r"(Total_de_carreras_11)_8077.pdf"
        )
        rep_path = Path(r"c:\Users\cdiaz\Downloads\0811_143238_CardRpt.txt")
        if not pdf_path.is_file() or not rep_path.is_file():
            return
        assert es_tela_oficial(pdf_path)
        datos_pdf = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(pdf_path))
        datos_rep, _ = normalizar_reporte(rep_path)
        buf: list = []
        imprimir_tabla_san_isidro(
            datos_pdf, datos_rep, tipo_pdf="TELA OFICIAL", imprimir=False, html_buffer=buf,
        )
        codigos = _codigos_ap_por_carrera(buf)[11]
        assert "EXA" not in codigos
        assert "TRI" not in codigos
        assert "IMP" in codigos
        assert "CUA" in codigos


def test_ter_en_oficial_no_en_reporte_es_error():
    """GAN/SEG/TER son presencia: TER en oficial y ausente en reporte ≠ [OK]."""
    from controlcomparador.config import SYM_FAIL
    from controlcomparador.ui.tables import _contar_fila_estado, _estado_apuesta

    pdf = {
        1: {
            "caballos": 11,
            "apuestas": {
                "GAN": None, "SEG": None, "TER": None,
                "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 2000.0,
            },
        },
    }
    rep = {
        1: {
            "caballos": 11,
            "apuestas": {
                "GAN": None, "SEG": None,
                "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 2000.0,
            },
        },
    }
    estado = _estado_apuesta(
        None, None, "OFICIAL", "reporte",
        en1=True, en2=False, codigo="TER",
    )
    assert SYM_FAIL in estado
    err, avisos = _contar_fila_estado(estado, 0, 0)
    assert err == 1
    assert avisos == 0

    buf: list = []
    bloque = imprimir_tabla_san_isidro(
        pdf, rep, tipo_pdf="OFICIAL", imprimir=False, html_buffer=buf,
    )
    codigos = _codigos_ap_por_carrera(buf)[1]
    assert "TER" in codigos
    assert "EXA" in codigos
    assert bloque.num_errores >= 1

    ter_apr = None
    carrera_actual = None
    for fila in buf[0]["filas"]:
        if fila[0]:
            carrera_actual = int(fila[0])
        if carrera_actual == 1 and fila[2] == "TER":
            ter_apr = fila[3]
    assert ter_apr == "-"
    assert buf[0]["columnas"][3] == "Ap.R"

    gan = _estado_apuesta(
        None, None, "OFICIAL", "reporte",
        en1=True, en2=True, codigo="GAN",
    )
    assert SYM_FAIL not in gan


def test_tabla_derecha_marca_extra_no_error():
    from controlcomparador.ui.tables import (
        _aviso_extra_oficial,
        _contar_fila_estado,
        _estado_posting_triple,
        imprimir_tabla_posting_vs_reporte,
    )

    estado = _estado_posting_triple(2000.0, None, 2000.0, "OFICIAL", codigo="EXA")
    assert estado == _aviso_extra_oficial()
    err, avisos = _contar_fila_estado(estado, 0, 0)
    assert err == 0
    assert avisos == 1

    estado_all = _estado_posting_triple(
        2000.0, None, 2000.0, "OFICIAL", codigo="EXA",
        en_pos=True, en_src=False, en_rep=False,
    )
    assert estado_all == _aviso_extra_oficial()
    err_all, avisos_all = _contar_fila_estado(estado_all, 0, 0)
    assert err_all == 0
    assert avisos_all == 1

    estado_dob = _estado_posting_triple(2000.0, None, 2000.0, "OFICIAL", codigo="DOB")
    assert "extra" not in estado_dob
    err_dob, avisos_dob = _contar_fila_estado(estado_dob, 0, 0)
    assert err_dob == 1
    assert avisos_dob == 0

    estado = _estado_posting_triple(
        None, None, None, "OFICIAL", codigo="TER",
        en_pos=False, en_src=True, en_rep=False,
    )
    err_ter, _ = _contar_fila_estado(estado, 0, 0)
    assert err_ter == 1

    pdf = {4: {"caballos": 13, "apuestas": {"IMP": 2000.0, "CUA": 1000.0}}}
    posting = ({4: {"EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0}}, set())
    reporte = ({4: {"EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0}}, set())
    rep_meta = {
        4: {
            "caballos": 13,
            "apuestas": {
                "IMP": None, "CUA": None, "EXA": None, "TRI": None, "DOB": None,
            },
            "bases": {
                "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0,
            },
        },
    }
    buf: list = []
    bloque = imprimir_tabla_posting_vs_reporte(
        posting, reporte, datos_fuente=pdf, datos_reporte_meta=rep_meta,
        label_fuente="OFICIAL", imprimir=False, html_buffer=buf,
    )
    estados = {f[2]: f[-1] for f in buf[0]["filas"]}
    assert estados["EXA"] == "extra"
    assert estados["TRI"] == "extra"
    assert "[ERR]" not in estados["EXA"]
    assert estados["DOB"] != "extra"
    assert bloque.num_errores >= 1
    assert bloque.num_avisos >= 2


def test_tabla_derecha_extra_all_solo_en_bases():
    """ALL EXA/TRI en B.RSM+posting, no en Ap.R ni oficial → extra, no error."""
    from controlcomparador.ui.tables import imprimir_tabla_posting_vs_reporte

    pdf = {
        4: {
            "caballos": 13,
            "apuestas": {"IMP": 2000.0, "CUA": 1000.0, "DOB": 2000.0},
        },
    }
    posting = ({
        4: {
            "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0,
        },
    }, set())
    reporte = ({
        4: {
            "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0,
        },
    }, set())
    rep_meta = {
        4: {
            "caballos": 13,
            "apuestas": {"IMP": None, "CUA": None, "DOB": None},
            "bases": {
                "EXA": 2000.0, "IMP": 2000.0, "TRI": 2000.0, "CUA": 1000.0, "DOB": 2000.0,
            },
        },
    }
    buf: list = []
    bloque = imprimir_tabla_posting_vs_reporte(
        posting, reporte, datos_fuente=pdf, datos_reporte_meta=rep_meta,
        label_fuente="OFICIAL", imprimir=False, html_buffer=buf,
    )
    estados = {f[2]: f[-1] for f in buf[0]["filas"]}
    assert estados["EXA"] == "extra"
    assert estados["TRI"] == "extra"
    assert "[ERR]" not in estados["EXA"]
    assert "[ERR]" not in estados["TRI"]
    assert estados["IMP"] != "extra"
    assert estados["DOB"] != "extra"
    assert bloque.num_errores == 0
    assert bloque.num_avisos >= 2


def test_imp_solo_en_apr_no_aparece_en_rsm():
    """IMP solo en AVAILABLE POOLS: error a la izquierda, no fila RSM a la derecha."""
    from controlcomparador.ui.tables import imprimir_tabla_posting_vs_reporte

    pdf = {
        6: {
            "caballos": 9,
            "apuestas": {
                "GAN": None, "SEG": None, "TER": None,
                "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 1000.0,
            },
        },
    }
    posting = ({
        6: {"EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 1000.0},
    }, set())
    reporte = ({
        6: {"EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 1000.0},
    }, set())
    rep = {
        6: {
            "caballos": 9,
            "apuestas": {
                "GAN": None, "SEG": None, "TER": None,
                "EXA": None, "TRI": None, "IMP": None, "DOB": None, "QTN": None,
            },
            "bases": {
                "EXA": 2000.0, "TRI": 2000.0, "DOB": 2000.0, "QTN": 1000.0,
            },
        },
    }

    buf_izq: list = []
    bloque_izq = imprimir_tabla_san_isidro(
        pdf, rep, tipo_pdf="OFICIAL", imprimir=False, html_buffer=buf_izq,
    )
    apr_imp = False
    ap_imp = None
    carrera_actual = None
    for fila in buf_izq[0]["filas"]:
        if fila[0]:
            carrera_actual = int(fila[0])
        if carrera_actual == 6 and fila[3] == "IMP":
            apr_imp = True
            ap_imp = fila[2]
    assert apr_imp
    assert ap_imp == "-"
    assert bloque_izq.num_errores >= 1
    assert any("IMP" in m and "reporte" in m for m in bloque_izq.mensajes)

    buf_der: list = []
    imprimir_tabla_posting_vs_reporte(
        posting, reporte, datos_fuente=pdf, datos_reporte_meta=rep,
        label_fuente="OFICIAL", imprimir=False, html_buffer=buf_der,
    )
    rsm_codigos = [f[2] for f in buf_der[0]["filas"]]
    assert "IMP" not in rsm_codigos
    assert "EXA" in rsm_codigos
    assert "TRI" in rsm_codigos
    assert "DOB" in rsm_codigos
    assert "QTN" in rsm_codigos


def test_caballos_8_7_en_html_sin_tags_rich():
    """Cab. mismatch va plano 8/7 al HTML; el Rich usa [fail]."""
    pdf = {10: {"caballos": 8, "apuestas": {"GAN": None, "EXA": 2000.0, "TER": None}}}
    rep = {10: {"caballos": 7, "apuestas": {"GAN": None, "EXA": None, "TER": None}}}
    buf: list = []
    imprimir_tabla_san_isidro(pdf, rep, tipo_pdf="OFICIAL", imprimir=False, html_buffer=buf)
    cab = None
    for fila in buf[0]["filas"]:
        if fila[0] == "10":
            cab = fila[1]
            break
    assert cab == "8/7"
    assert "[fail]" not in cab
    """TRI en AVAILABLE POOLS y no en oficial: Ap. '-', Ap.R TRI, estado [ERR]."""
    from controlcomparador.config import SYM_FAIL
    from controlcomparador.ui.tables import _estado_apuesta

    estado = _estado_apuesta(
        None, None, "OFICIAL", "reporte",
        en1=False, en2=True, codigo="TRI", permitir_extra=False,
    )
    assert SYM_FAIL in estado
    assert "extra" not in estado.lower()

    pdf = {
        10: {
            "caballos": 8,
            "apuestas": {
                "GAN": None, "SEG": None, "TER": None,
                "EXA": 2000.0, "DOB": 2000.0, "QTP": 1000.0, "CUA": 1000.0,
            },
        },
    }
    rep = {
        10: {
            "caballos": 8,
            "apuestas": {
                "GAN": None, "SEG": None, "TER": None,
                "EXA": None, "TRI": None, "CUA": None, "DOB": None, "QTP": None,
            },
            "bases": {
                "EXA": 2000.0, "CUA": 1000.0, "DOB": 2000.0, "QTP": 1000.0,
            },
        },
    }
    buf: list = []
    bloque = imprimir_tabla_san_isidro(
        pdf, rep, tipo_pdf="OFICIAL", imprimir=False, html_buffer=buf,
    )
    assert "Bases RSM" in buf[0]["columnas"] or "BASES RSM TABLE" in buf[0]["columnas"]
    ap_tri = apr_tri = bases_tri = estado_tri = None
    carrera_actual = None
    for fila in buf[0]["filas"]:
        if fila[0]:
            carrera_actual = int(fila[0])
        if carrera_actual == 10 and (fila[2] == "TRI" or fila[3] == "TRI"):
            ap_tri, apr_tri = fila[2], fila[3]
            bases_tri, estado_tri = fila[5], fila[-1]
    assert ap_tri == "-"
    assert apr_tri == "TRI"
    assert bases_tri == "-"
    assert "extra" not in (estado_tri or "").lower()
    assert bloque.num_errores >= 1
    assert any("TRI" in m and "reporte" in m and "oficial" in m for m in bloque.mensajes)

    import io
    import sys
    from controlcomparador.ui.tables import (
        imprimir_par_comparacion,
        imprimir_tabla_posting_vs_reporte,
        mostrar_resumenes_consolidado,
    )
    from controlcomparador.ui.console import console

    posting = ({10: {"EXA": 2000.0, "DOB": 2000.0, "QTP": 1000.0, "CUA": 1000.0}}, set())
    bloque_izq = imprimir_tabla_san_isidro(
        pdf, rep, posting, tipo_pdf="OFICIAL", imprimir=False, compacto=True, par=True,
    )
    bloque_der = imprimir_tabla_posting_vs_reporte(
        posting, ({10: {"EXA": 2000.0, "DOB": 2000.0, "QTP": 1000.0, "CUA": 1000.0}}, set()),
        datos_fuente=pdf, datos_reporte_meta=rep, label_fuente="OFICIAL",
        imprimir=False, compacto=True, par=True,
    )
    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    console.width = 160
    try:
        imprimir_par_comparacion(bloque_izq, bloque_der)
        salida_par = cap.getvalue()
        cap.seek(0)
        cap.truncate(0)
        mostrar_resumenes_consolidado(
            [("OFICIAL vs REPORTE", False, list(bloque_izq.mensajes))],
            titulo_panel="DIFERENCIAS DETECTADAS",
        )
        salida_panel = cap.getvalue()
    finally:
        sys.stdout = old
    assert "TRI está de más en el reporte" not in salida_par
    assert "DIFERENCIAS DETECTADAS" in salida_panel
    assert "TRI está de más en el reporte" in salida_panel
    assert "no está en el oficial" in salida_panel

