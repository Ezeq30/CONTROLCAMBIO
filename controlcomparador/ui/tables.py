# -*- coding: utf-8 -*-
"""Tablas Rich, export HTML y vista par de consola (posting lado a lado).

Vista par (San Isidro, Palermo, La Plata con posting):
  - Izquierda: fuente vs reporte (6 cols, sin Post.).
  - Derecha: posting vs fuente vs reporte (7 cols).
  - ``imprimir_par_comparacion`` une títulos + tablas sin Panel exterior.
  - ``_imprimir_renderables_pegados`` captura segmentos Rich y escribe ancho
    fijo vía ``escribir_salida_fija`` (evita huecos en consola Windows ancha).
  - ``ancho_fijo=True`` en títulos: centrados con ``str.center(ancho)``.
  - Tablas: ``_recortar_padding_rich`` evita padding fantasma de Rich al capturar.
  - La Plata par: ``add_section()`` alinea carreras; mensajes Estado <= 13 cols.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.segment import Segment, Segments
from rich.text import Text

from rich import box

from datetime import datetime
from pathlib import Path

from collections import defaultdict
from controlcomparador.config import (
    ORDEN_APUESTAS, SYM_OK, SYM_FAIL, APUESTAS_PICK,
    PASES_POR_APUESTA, PASE_ORDER, APUESTAS_SIN_COMPARAR_VALOR,
    APUESTAS_CARRERAS_ALL,
)
from controlcomparador.parsers.pdf import extraer_info_reunion_tela
from controlcomparador.ui.console import console, ampliar_consola_windows, escribir_salida_fija, tema

SeccionComparacionHtml = dict[str, Any]


# ---------------------------------------------------------------------------
# Vista par: dos tablas pegadas en consola (posting)
# ---------------------------------------------------------------------------


@dataclass
class BloqueComparacion:
    """Resultado renderizable de una comparación (título + tabla Rich + contadores)."""
    titulo: str
    tabla: Table
    num_carreras: int
    num_errores: int
    num_avisos: int = 0
    subtitulo: Optional[str] = None


def _texto_resumen_bloque(bloque: BloqueComparacion) -> Optional[str]:
    if bloque.num_errores == 0 and bloque.num_avisos == 0:
        return f"[ok]{bloque.num_carreras} carreras · sin diferencias[/ok]"
    if bloque.num_errores == 0:
        return None
    return f"[fail]{bloque.num_errores} fila(s) con diferencia[/fail]"


def _imprimir_bloque_comparacion_desde_bloque(bloque: BloqueComparacion) -> None:
    resumen = _texto_resumen_bloque(bloque)
    if bloque.subtitulo:
        console.print(f"[info]{bloque.subtitulo}[/info]")
    console.print(Panel(
        bloque.tabla,
        title=f"[bold]{bloque.titulo}[/bold]",
        border_style="#2e7d32",
        padding=(0, 0),
        expand=False,
    ))
    if resumen:
        console.print(resumen)
    console.print()


def _capturar_lineas_segmentos(renderable, width: int) -> list[list[Segment]]:
    """Renderiza un Rich renderable a líneas de Segmentos con ancho forzado."""
    ancho_prev = console.width
    console.width = width
    try:
        options = console.options.update(width=width, max_width=width)
        return console.render_lines(renderable, options)
    finally:
        console.width = ancho_prev


def _pad_linea_segmentos(linea: list[Segment], ancho: int) -> list[Segment]:
    largo = Segment.get_line_length(linea)
    if largo < ancho:
        return linea + [Segment(" " * (ancho - largo))]
    return linea


def _recortar_padding_rich(linea: list[Segment]) -> list[Segment]:
    """Quita espacios finales que Rich agrega al capturar con ancho > contenido.

    Sin esto, una fila ancha (p. ej. estado largo) infla el ancho de captura y
    el resto de filas quedan con padding trailing → hueco visible entre tablas.
    """
    if not linea:
        return linea
    out = list(linea)
    while out:
        seg = out[-1]
        txt = seg.text or ""
        if not txt.strip():
            out.pop()
            continue
        rs = txt.rstrip()
        if len(rs) < len(txt):
            if rs:
                out[-1] = Segment(rs, seg.style)
            else:
                out.pop()
        break
    return out


def _largo_visible_linea(linea: list[Segment]) -> int:
    return Segment.get_line_length(_recortar_padding_rich(linea))


def _imprimir_renderables_pegados(
    render_izq,
    render_der,
    ancho_izq: int,
    ancho_der: int,
    *,
    ancho_fijo: bool = False,
) -> None:
    """Imprime dos bloques Rich en la misma fila, pegados, sin hueco.

    Args:
        render_izq, render_der: Text o Table de Rich.
        ancho_izq, ancho_der: pistas de captura (tablas: recalculados tras recorte).
        ancho_fijo: True para títulos centrados; no recortar ni recalcular ancho.
    """
    from io import StringIO

    ancho_izq_in = ancho_izq
    ancho_der_in = ancho_der
    lineas_izq = _capturar_lineas_segmentos(render_izq, ancho_izq)
    lineas_der = _capturar_lineas_segmentos(render_der, ancho_der)
    if not ancho_fijo:
        lineas_izq = [_recortar_padding_rich(l) for l in lineas_izq]
        lineas_der = [_recortar_padding_rich(l) for l in lineas_der]
        if lineas_izq:
            ancho_izq = max(_largo_visible_linea(l) for l in lineas_izq)
        if lineas_der:
            ancho_der = max(_largo_visible_linea(l) for l in lineas_der)
    else:
        ancho_izq = ancho_izq_in
        ancho_der = ancho_der_in
    altura = max(len(lineas_izq), len(lineas_der))
    blanco_izq = [Segment(" " * ancho_izq)]
    blanco_der = [Segment(" " * ancho_der)]
    while len(lineas_izq) < altura:
        lineas_izq.append(blanco_izq)
    while len(lineas_der) < altura:
        lineas_der.append(blanco_der)
    ancho_total = ancho_izq + ancho_der
    ampliar_consola_windows(ancho_total + 2)
    console.width = ancho_total
    buf = StringIO()
    impresor = Console(
        file=buf,
        width=ancho_total,
        force_terminal=True,
        soft_wrap=False,
        theme=tema,
        legacy_windows=console.legacy_windows,
    )
    for izq, der in zip(lineas_izq, lineas_der):
        linea = _pad_linea_segmentos(izq, ancho_izq) + _pad_linea_segmentos(der, ancho_der)
        impresor.print(
            Segments(linea + [Segment.line()]),
            crop=False,
            overflow="ignore",
            width=ancho_total,
            soft_wrap=False,
        )
    escribir_salida_fija(buf.getvalue())


def _titulo_par_texto(texto: str, ancho: int) -> Text:
    """Título verde centrado en exactamente ``ancho`` columnas (vista par)."""
    contenido = texto[:ancho] if len(texto) > ancho else texto.center(ancho)
    t = Text(contenido, style="bold #2e7d32")
    t.no_wrap = True
    return t


def _ancho_hint_inicial(renderable) -> int:
    if isinstance(renderable, Table) and renderable.columns:
        base = sum(
            getattr(c, "width", None) or getattr(c, "min_width", None) or 1
            for c in renderable.columns
        )
        return max(base + len(renderable.columns) * 2 + 2, 20)
    return 1


def _linea_truncada(linea: list[Segment]) -> bool:
    return any("\u2026" in (seg.text or "") for seg in linea)


def _ancho_minimo_renderable(renderable) -> int:
    """Ancho mínimo de tabla sin truncar celdas (Rich puede insertar …)."""
    ancho = _ancho_hint_inicial(renderable)
    for _ in range(30):
        lineas = _capturar_lineas_segmentos(renderable, ancho)
        if not lineas:
            return max(ancho, 1)
        necesario = max(_largo_visible_linea(l) for l in lineas)
        truncada = any(_linea_truncada(l) for l in lineas)
        if truncada or necesario > ancho:
            ancho = max(ancho + 1, necesario)
            continue
        return necesario
    return ancho


def _preparar_par_sin_panel(
    bloque_izq: BloqueComparacion,
    bloque_der: BloqueComparacion,
) -> tuple[Optional[str], Text, Text, Table, Table, int, int]:
    """Prepara títulos, tablas y anchos medidos para ``imprimir_par_comparacion``."""
    subtitulo = bloque_izq.subtitulo or bloque_der.subtitulo
    titulo_izq = _titulo_panel_izq(bloque_izq.titulo)
    titulo_der = _titulo_panel_der(bloque_der.titulo)
    ancho_izq = _ancho_minimo_renderable(bloque_izq.tabla)
    ancho_der = _ancho_minimo_renderable(bloque_der.tabla)
    return (
        subtitulo,
        _titulo_par_texto(titulo_izq, ancho_izq),
        _titulo_par_texto(titulo_der, ancho_der),
        bloque_izq.tabla,
        bloque_der.tabla,
        ancho_izq,
        ancho_der,
    )


def _imprimir_resumen_par(bloque_izq: BloqueComparacion, bloque_der: BloqueComparacion) -> None:
    hay_diff = any(b.num_errores > 0 for b in (bloque_izq, bloque_der))
    if hay_diff:
        for bloque in (bloque_izq, bloque_der):
            resumen = _texto_resumen_bloque(bloque)
            if resumen:
                console.print(f"[dim]{bloque.titulo}:[/dim] {resumen}")
    console.print()


def imprimir_par_comparacion(bloque_izq: BloqueComparacion, bloque_der: BloqueComparacion) -> None:
    """Dos tablas lado a lado: títulos centrados + tablas ROUNDED pegadas.

    Usado por San Isidro, Palermo y La Plata cuando hay posting (auto-detect / menú).
    """
    subtitulo, tit_izq, tit_der, tabla_izq, tabla_der, ancho_izq, ancho_der = (
        _preparar_par_sin_panel(bloque_izq, bloque_der)
    )
    if subtitulo:
        console.print(f"[info]{subtitulo}[/info]")
    _imprimir_renderables_pegados(tit_izq, tit_der, ancho_izq, ancho_der, ancho_fijo=True)
    _imprimir_renderables_pegados(tabla_izq, tabla_der, ancho_izq, ancho_der)
    _imprimir_resumen_par(bloque_izq, bloque_der)


_HTML_CSS_COMPARACION = """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; padding: 15px; background: #fff; color: #333; }
  .container { width: 100%; max-width: 98vw; border: 1px solid #c8e6c9; border-radius: 6px; overflow: hidden; margin-bottom: 16px; }
  .header { background: #1b5e20; color: #fff; padding: 10px 14px; }
  .header h1 { font-size: 14px; font-weight: 600; }
  .meta { font-size: 11px; color: #e8f5e9; margin-top: 4px; }
  .subtitle { font-size: 12px; font-weight: 600; color: #2e7d32; padding: 8px 14px 4px; background: #f1f8e9; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #1b5e20; color: #fff; padding: 5px 10px; text-align: left; font-weight: 600; }
  th.right, td.right { text-align: right; }
  th.center, td.center { text-align: center; }
  td { padding: 3px 10px; border-bottom: 1px solid #e0e0e0; }
  td.dim { color: #999; }
  td.ok { color: #2e7d32; font-weight: 600; }
  td.diff { color: #c62828; font-weight: 600; }
  td.bet { color: #2e7d32; font-weight: 600; }
  td.warn { color: #e65100; font-weight: 600; }
  tr:nth-child(even) { background: #f1f8e9; }
  tr.carrera-start td { border-top: 2px solid #c8e6c9; }
  .diff-list { padding: 8px 14px 12px; font-size: 12px; }
  .diff-list li { color: #c62828; margin: 2px 0; }
  .two-col-row { display: flex; gap: 10px; align-items: flex-start; padding: 0 0 8px; }
  .col-panel { flex: 1; min-width: 0; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
  .col-panel .subtitle { margin: 0; }
  .col-panel table { font-size: 11px; table-layout: fixed; width: 100%; }
  .col-panel th, .col-panel td { padding: 2px 6px; overflow: hidden; text-overflow: ellipsis; }
  .col-panel th.num, .col-panel td.num { text-align: right; }
  .col-panel th.center, .col-panel td.center { text-align: center; }
  @media print {
    body { padding: 10px; }
    .header, th { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    tr:nth-child(even) { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def _ordenar_codigos(codigos: set[str]) -> list[str]:
    def key(cod):
        try:
            return (0, ORDEN_APUESTAS.index(cod))
        except ValueError:
            return (1, cod)
    return sorted(codigos, key=key)


def _es_fuente_planilla(label: Optional[str]) -> bool:
    return (label or "").strip().upper() in ("PLANILLA", "LA PLATA")


def _codigos_vista_par_laplata(codigos: set[str]) -> list[str]:
    """Orden de apuestas en par La Plata; excluye GAN/SEG/TER del lado posting."""
    return _ordenar_codigos(codigos - APUESTAS_SIN_COMPARAR_VALOR)


def _codigos_carrera_par_laplata(
    ap_plan: dict,
    ap_rep: dict,
    pos_ap: Optional[dict] = None,
) -> list[str]:
    """Unión planilla|reporte|posting para alinear filas izq/der en par La Plata."""
    raw = set(ap_plan.keys()) | set(ap_rep.keys())
    if pos_ap is not None:
        raw |= set(pos_ap.keys())
    return _codigos_vista_par_laplata(raw)


def formato_valor(v: Optional[float]) -> str:
    if v is None:
        return "-"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.2f}"


def _celda_valor_rich(valor: Optional[float], referencia: Optional[float]) -> str:
    texto = formato_valor(valor)
    if valor is None:
        return f"[dimval]{texto}[/dimval]"
    if referencia is not None and valor != referencia:
        return f"[fail]{texto}[/fail]"
    return f"[ok]{texto}[/ok]"


def _nombre_fuente_corto(etiq: str) -> str:
    u = etiq.strip().upper()
    if "TELA" in u:
        return "tela"
    if u == "PLANILLA":
        return "planilla"
    if "BASES" in u:
        return "bases"
    if u == "OFICIAL":
        return "oficial"
    return etiq.lower().split()[0]


def _header_columna_fuente(etiq: str, *, par: bool = False, compacto: bool = False) -> str:
    u = (etiq or "OFICIAL").strip().upper()
    if "TELA" in u and "OFICIAL" in u:
        return "Tela Oficial"
    if "TELA" in u:
        return "Tela"
    if u == "OFICIAL":
        return "Oficial"
    if "PALERMO" in u or "BASES" in u:
        return "Bases"
    if "PLANILLA" in u:
        return "Planilla"
    return etiq.strip().title() or "Oficial"


def _header_columna_posting(*, par: bool = False) -> str:
    return "Post." if par else "Posting"


def _header_columna_reporte(*, par: bool = False) -> str:
    return "Rep." if par else "Reporte"


def _kwargs_col_fuente(etiq: str, *, compacto: bool = False, par: bool = False) -> tuple[str, dict]:
    nombre = _header_columna_fuente(etiq, par=par, compacto=compacto)
    wv = _ancho_valor(compacto=compacto, par=par)
    ancho = max(wv, len(nombre))
    return nombre, {"justify": "right", "width": ancho, "min_width": wv, "no_wrap": True}


def _caballos_str(
    num_carrera: int,
    datos_fuente: Optional[dict],
    datos_reporte_meta: Optional[dict],
) -> str:
    fuente = (datos_fuente or {}).get(num_carrera, {})
    rep = (datos_reporte_meta or {}).get(num_carrera, {})
    c_src = fuente.get("caballos", "?") if isinstance(fuente, dict) else "?"
    c_rep = rep.get("caballos", "?") if isinstance(rep, dict) else "?"
    return f"{c_src}/{c_rep}"


def _texto_aviso_no_en(etiq: str) -> str:
    """Texto plano de ausencia en fuente; debe caber en columna Estado par (13 cols)."""
    corto = _nombre_fuente_corto(etiq)
    if corto == "planilla":
        return "no planilla"
    if corto in ("reporte", "posting"):
        return f"no en {corto}"
    return f"no {corto}"


def _aviso_no_en_fuente(etiq: str) -> str:
    return f"[dim yellow]{_texto_aviso_no_en(etiq)}[/dim yellow]"


def _aviso_no_en_reporte() -> str:
    return "[dim yellow]no en reporte[/dim yellow]"


def _aviso_no_en_posting() -> str:
    return "[dim yellow]no en posting[/dim yellow]"


def _kwargs_col_estado(*, compacto: bool = False, par: bool = False) -> dict:
    if compacto or par:
        return {"justify": "left", "width": 13, "no_wrap": True}
    return {"justify": "center", "width": 13, "no_wrap": True}


def _ancho_valor(*, compacto: bool = False, par: bool = False) -> int:
    if par:
        return 6
    return 7 if compacto else 8


def _ancho_carrera(*, compacto: bool = False, par: bool = False) -> int:
    return 5


def _ancho_apuesta(*, compacto: bool = False, par: bool = False) -> int:
    return 3 if par else 4


def _ancho_caballos(*, compacto: bool = False, par: bool = False) -> int:
    if par:
        return 6
    return 6 if compacto else 7


def _kwargs_col_caballos(*, compacto: bool = False, par: bool = False) -> dict:
    return {
        "justify": "center",
        "width": _ancho_caballos(compacto=compacto, par=par),
        "min_width": 5,
        "no_wrap": True,
    }


def _perfil_columnas_comparacion(
    etiq_fuente: str,
    *,
    con_posting: bool = False,
    compacto: bool = False,
    par: bool = False,
) -> list[tuple[str, dict]]:
    """Columnas unificadas: Carr.|Cab.|Ap.|Fuente|Rep.|[Post.]|Estado.

    Modo ``par=True``: headers cortos (Rep., Post.), anchos compactos; en vista par
    la tabla izquierda suele llamarse con ``con_posting=False`` (6 cols).
    """
    wv = _ancho_valor(compacto=compacto, par=par)
    wc = _ancho_carrera(compacto=compacto, par=par)
    wa = _ancho_apuesta(compacto=compacto, par=par)
    col_fuente, kwargs_fuente = _kwargs_col_fuente(etiq_fuente, compacto=compacto, par=par)
    columnas: list[tuple[str, dict]] = [
        ("Carr.", {"style": "carrera", "width": wc, "justify": "center"}),
        ("Cab.", _kwargs_col_caballos(compacto=compacto, par=par)),
        ("Ap.", {"style": "codigo", "width": wa, "min_width": wa, "no_wrap": True}),
        (col_fuente, kwargs_fuente),
        (_header_columna_reporte(par=par), {"justify": "right", "width": wv}),
    ]
    if con_posting:
        columnas.append((_header_columna_posting(par=par), {"justify": "right", "width": wv}))
    columnas.append(("Estado", _kwargs_col_estado(compacto=compacto, par=par)))
    return columnas


def _titulo_panel_izq(titulo: str) -> str:
    t = titulo.removeprefix("COMPARACION ").strip()
    return t.replace(" vs REPORTE", " vs Reporte")


def _titulo_panel_der(titulo: str) -> str:
    raw = titulo.removeprefix("COMPARACION ").strip()
    if "POSTING" not in raw.upper():
        return _titulo_panel_izq(titulo)
    partes = [
        p.strip()
        for p in raw.replace("·", "|").split("|")
        if p.strip().upper() not in ("POSTING", "REPORTE")
    ]
    fuente = " ".join(partes).strip().title() or "Oficial"
    return f"Posting Vs {fuente} vs Reporte"


def _msg_no_en(fuente: str) -> str:
    f = fuente.strip().lower()
    if f in ("reporte", "rep.", "rep"):
        return _aviso_no_en_reporte()
    if f in ("posting", "post.", "post"):
        return _aviso_no_en_posting()
    return _aviso_no_en_fuente(fuente)


def _crear_tabla_comparacion(
    columnas: list[tuple[str, dict]],
    *,
    par: bool = False,
    compacto: bool = False,
) -> Table:
    t = Table(
        box=box.ROUNDED,
        header_style="header",
        border_style="#2e7d32",
        show_lines=False,
        pad_edge=False,
        padding=(0, 1),
        expand=False,
    )
    for nombre, kwargs in columnas:
        t.add_column(nombre, **kwargs)
    return t


def _imprimir_bloque_comparacion(
    titulo: str,
    tabla: Table,
    num_carreras: int,
    num_errores: int,
    subtitulo: Optional[str] = None,
    num_avisos: int = 0,
) -> None:
    _imprimir_bloque_comparacion_desde_bloque(BloqueComparacion(
        titulo=titulo,
        tabla=tabla,
        num_carreras=num_carreras,
        num_errores=num_errores,
        num_avisos=num_avisos,
        subtitulo=subtitulo,
    ))


def _fila_es_error(estado_markup: str) -> bool:
    return SYM_FAIL in estado_markup


def _fila_es_aviso(estado_markup: str) -> bool:
    return not _fila_es_error(estado_markup) and "no en " in estado_markup.lower()


def _fila_es_diferencia(estado_markup: str) -> bool:
    return _fila_es_error(estado_markup)


def _contar_fila_estado(estado_markup: str, errores: int, avisos: int) -> tuple[int, int]:
    if _fila_es_error(estado_markup):
        return errores + 1, avisos
    if _fila_es_aviso(estado_markup):
        return errores, avisos + 1
    return errores, avisos


def _registrar_seccion_html(
    buffer: Optional[list[SeccionComparacionHtml]],
    titulo: str,
    columnas: list[str],
    filas: list[list[str]],
    html_col: Optional[str] = None,
) -> None:
    if buffer is None:
        return
    sec: SeccionComparacionHtml = {
        "titulo": titulo, "columnas": columnas, "filas": [list(f) for f in filas],
    }
    if html_col:
        sec["html_col"] = html_col
    buffer.append(sec)


def _apuestas_flat_por_carrera(datos: dict) -> dict[int, dict[str, Optional[float]]]:
    """Normaliza datos PDF/planilla a {carrera: {codigo: valor}}."""
    flat: dict[int, dict[str, Optional[float]]] = {}
    for num, d in datos.items():
        if isinstance(d, dict) and "apuestas" in d:
            flat[num] = d.get("apuestas", {})
        elif isinstance(d, dict):
            flat[num] = d
    return flat


def _estado_posting_triple(
    v_pos: Optional[float],
    v_fuente: Optional[float],
    v_rep: Optional[float],
    etiq_fuente: str,
) -> str:
    """Posting debe alinearse con reporte y con tela/oficial/planilla."""
    if v_pos == v_rep:
        if v_fuente is None and v_rep is not None:
            return _msg_no_en(etiq_fuente)
        if v_fuente is None or v_fuente == v_pos:
            return f"[green]{SYM_OK}[/green]"
    if v_pos is None and v_rep is None and v_fuente is None:
        return f"[green]{SYM_OK}[/green]"
    if v_pos is None:
        if v_rep is not None and v_fuente is not None and v_rep == v_fuente:
            return _aviso_no_en_posting()
        if v_rep is not None:
            return _aviso_no_en_reporte()
        if v_fuente is not None:
            return _msg_no_en(etiq_fuente)
    if v_rep is None:
        if v_pos is not None and v_fuente is not None and v_pos == v_fuente:
            return _aviso_no_en_reporte()
        if v_pos is not None:
            return _aviso_no_en_posting()
    if v_fuente is None:
        return _estado_apuesta(v_pos, v_rep, "posting", "reporte")
    return f"[red]{SYM_FAIL}[/red]"


_RICH_TAG_RE = re.compile(r"\[/?[^\]]+\]")


def _estado_plano(estado_markup: str) -> str:
    return _RICH_TAG_RE.sub("", estado_markup)


def _estado_apuesta(v1: Optional[float], v2: Optional[float], etiq1: str, etiq2: str) -> str:
    if v1 == v2:
        return f"[green]{SYM_OK}[/green]"
    if v1 is None:
        return _msg_no_en(etiq1)
    if v2 is None:
        return _aviso_no_en_reporte()
    return f"[red]{SYM_FAIL}[/red]"


def _estado_tres_fuentes(
    v_pdf: Optional[float],
    v_rep: Optional[float],
    v_pos: Optional[float],
    label_fuente: str,
) -> str:
    if v_pdf == v_rep and (v_pos is None or v_pos == v_rep):
        return f"[green]{SYM_OK}[/green]"
    if v_pdf is None:
        if v_rep is not None and v_pos is not None and v_rep == v_pos:
            return _msg_no_en(label_fuente)
        if v_rep is not None and v_pos is not None:
            return f"[red]{SYM_FAIL}[/red]"
        if v_rep is not None:
            return _msg_no_en(label_fuente)
        return _aviso_no_en_posting()
    if v_rep is None:
        if v_pos is not None and v_pos == v_pdf:
            return _aviso_no_en_posting()
        return _aviso_no_en_reporte()
    if v_pos is not None and v_pos != v_rep:
        return f"[red]{SYM_FAIL}[/red]"
    return f"[red]{SYM_FAIL}[/red]"


def _html_clases_columna(col: str) -> tuple[str, str]:
    """Retorna (clase th, clase td base) para alineación HTML."""
    if col == "Estado":
        return "center", "center"
    if col in ("Ap.", "Apuesta"):
        return "", ""
    if col in ("Carr.", "Carrera", "Cab.", "Caballos"):
        return "center", "center"
    if col in ("Post", "Post.", "Rep", "Rep.", "Posting", "Reporte", "Oficial", "Ofic", "Tela", "Tela Oficial", "Bases", "Planilla", "Base", "Plan"):
        return "num", "num"
    return "num", "num"


def imprimir_tabla_san_isidro(
    datos_pdf: dict,
    datos_reporte: dict,
    datos_posting: Optional[tuple[dict, set[str]]] = None,
    fecha_reporte: Optional[str] = None,
    tipo_pdf: Optional[str] = None,
    html_buffer: Optional[list[SeccionComparacionHtml]] = None,
    imprimir: bool = True,
    compacto: bool = False,
    par: bool = False,
) -> BloqueComparacion:
    valores_posting = datos_posting[0] if datos_posting else {}
    label_pdf = tipo_pdf or "OFICIAL"
    titulo = f"COMPARACION {label_pdf} vs REPORTE"

    columnas_def = _perfil_columnas_comparacion(
        label_pdf,
        con_posting=bool(datos_posting),
        compacto=compacto,
        par=par,
    )

    t = _crear_tabla_comparacion(columnas_def, par=par, compacto=compacto)
    nombres_cols = [c[0] for c in columnas_def]
    filas_html: list[list[str]] = []
    num_errores = 0
    num_avisos = 0

    todas = sorted(set(datos_pdf.keys()) | set(datos_reporte.keys()))
    for num_carrera in todas:
        pdf = datos_pdf.get(num_carrera, {})
        rep = datos_reporte.get(num_carrera, {})
        pdf_ap = pdf.get("apuestas", {}) if pdf else {}
        rep_ap = rep.get("apuestas", {}) if rep else {}
        pos_ap = valores_posting.get(num_carrera, {})
        c_pdf = pdf.get("caballos", "?") if pdf else "?"
        c_rep = rep.get("caballos", "?") if rep else "?"
        cab_str = f"{c_pdf}/{c_rep}"

        todos_codigos = _ordenar_codigos(set(pdf_ap.keys()) | set(rep_ap.keys()))
        for idx, cod in enumerate(todos_codigos):
            v_pdf = pdf_ap.get(cod)
            v_rep = rep_ap.get(cod)
            v_pos = pos_ap.get(cod) if datos_posting else None
            if datos_posting:
                estado = _estado_tres_fuentes(v_pdf, v_rep, v_pos, label_pdf)
            else:
                estado = _estado_apuesta(v_pdf, v_rep, label_pdf, "reporte")
            num_errores, num_avisos = _contar_fila_estado(estado, num_errores, num_avisos)

            if idx == 0 and num_carrera != todas[0]:
                t.add_section()

            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""

            celdas = [
                carrera_str,
                cab_show,
                f"[codigo]{cod}[/codigo]",
                _celda_valor_rich(v_pdf, v_rep),
                _celda_valor_rich(v_rep, v_pdf),
            ]
            if datos_posting:
                celdas.append(_celda_valor_rich(v_pos, v_rep))
            celdas.append(estado)
            t.add_row(*celdas)

            fila_plana = [
                carrera_str, cab_show, cod,
                formato_valor(v_pdf), formato_valor(v_rep),
            ]
            if datos_posting:
                fila_plana.append(formato_valor(v_pos))
            fila_plana.append(_estado_plano(estado))
            filas_html.append(fila_plana)

    subtitulo = f"Fecha del reporte: {fecha_reporte}" if fecha_reporte else None
    bloque = BloqueComparacion(
        titulo=titulo, tabla=t, num_carreras=len(todas),
        num_errores=num_errores, num_avisos=num_avisos, subtitulo=subtitulo,
    )
    _registrar_seccion_html(
        html_buffer, titulo, nombres_cols, filas_html,
        html_col="izq" if datos_posting else None,
    )
    if imprimir:
        _imprimir_bloque_comparacion_desde_bloque(bloque)
    return bloque


def imprimir_tablas_palermo(
    datos_pdf: dict,
    datos_reporte: tuple,
    fechas: list[str],
    fecha_usada: Optional[str],
    datos_posting: Optional[tuple[dict, set[str]]] = None,
    html_buffer: Optional[list[SeccionComparacionHtml]] = None,
    imprimir: bool = True,
    compacto: bool = False,
    par: bool = False,
) -> BloqueComparacion:
    valores_reporte, _ = datos_reporte
    valores_posting = datos_posting[0] if datos_posting else {}
    titulo = "COMPARACION BASES PALERMO vs REPORTE"

    columnas_def = _perfil_columnas_comparacion(
        "BASES PALERMO",
        con_posting=bool(datos_posting) and not par,
        compacto=compacto,
        par=par,
    )

    t = _crear_tabla_comparacion(columnas_def, par=par, compacto=compacto)
    nombres_cols = [c[0] for c in columnas_def]
    filas_html: list[list[str]] = []
    num_errores = 0
    num_avisos = 0
    incluir_posting_col = bool(datos_posting) and not par

    todas = sorted(set(datos_pdf.keys()) | set(valores_reporte.keys()))
    for num_carrera in todas:
        ap_bases = datos_pdf.get(num_carrera, {})
        ap_rep = valores_reporte.get(num_carrera, {})
        pos_ap = valores_posting.get(num_carrera, {})
        cab_str = "?/?"

        todos_codigos = _ordenar_codigos(set(ap_bases.keys()) | set(ap_rep.keys()))
        for idx, cod in enumerate(todos_codigos):
            v_bases = ap_bases.get(cod)
            v_rep = ap_rep.get(cod)
            v_pos = pos_ap.get(cod) if incluir_posting_col else None
            if incluir_posting_col:
                estado = _estado_tres_fuentes(v_bases, v_rep, v_pos, "Bases Palermo")
            else:
                estado = _estado_apuesta(v_bases, v_rep, "Bases Palermo", "reporte")
            num_errores, num_avisos = _contar_fila_estado(estado, num_errores, num_avisos)

            if idx == 0 and num_carrera != todas[0]:
                t.add_section()

            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""
            celdas = [
                carrera_str, cab_show, f"[codigo]{cod}[/codigo]",
                _celda_valor_rich(v_bases, v_rep),
                _celda_valor_rich(v_rep, v_bases),
            ]
            if incluir_posting_col:
                celdas.append(_celda_valor_rich(v_pos, v_rep))
            celdas.append(estado)
            t.add_row(*celdas)

            fila = [carrera_str, cab_show, cod, formato_valor(v_bases), formato_valor(v_rep)]
            if incluir_posting_col:
                fila.append(formato_valor(v_pos))
            fila.append(_estado_plano(estado))
            filas_html.append(fila)

    partes_sub: list[str] = []
    if fechas:
        partes_sub.append(f"Fechas detectadas: {', '.join(fechas)}")
    if fecha_usada:
        partes_sub.append(f"Fecha usada: {fecha_usada}")
    subtitulo = " · ".join(partes_sub) if partes_sub else None
    bloque = BloqueComparacion(
        titulo=titulo, tabla=t, num_carreras=len(todas),
        num_errores=num_errores, num_avisos=num_avisos, subtitulo=subtitulo,
    )
    _registrar_seccion_html(
        html_buffer, titulo, nombres_cols, filas_html,
        html_col="izq" if datos_posting else None,
    )
    if imprimir:
        _imprimir_bloque_comparacion_desde_bloque(bloque)
    return bloque


def imprimir_tabla_laplata(
    datos_planilla: dict,
    datos_reporte: dict,
    datos_posting: Optional[tuple[dict, set[str]]] = None,
    html_buffer: Optional[list[SeccionComparacionHtml]] = None,
    imprimir: bool = True,
    compacto: bool = False,
    par: bool = False,
) -> BloqueComparacion:
    valores_posting = datos_posting[0] if datos_posting else {}
    titulo = "COMPARACION PLANILLA vs REPORTE - LA PLATA"

    columnas_def = _perfil_columnas_comparacion(
        "PLANILLA",
        con_posting=bool(datos_posting) and not par,
        compacto=compacto,
        par=par,
    )

    t = _crear_tabla_comparacion(columnas_def, par=par, compacto=compacto)
    nombres_cols = [c[0] for c in columnas_def]
    filas_html: list[list[str]] = []
    num_errores = 0
    num_avisos = 0
    incluir_posting_col = bool(datos_posting) and not par

    todas = sorted(set(datos_planilla.keys()) | set(datos_reporte.keys()))
    for num_carrera in todas:
        plan = datos_planilla.get(num_carrera, {})
        rep = datos_reporte.get(num_carrera, {})
        ap_plan = plan.get("apuestas", {}) if plan else {}
        ap_rep = rep.get("apuestas", {}) if rep else {}
        pos_ap = valores_posting.get(num_carrera, {})
        c_plan = plan.get("caballos", "?") if plan else "?"
        c_rep = rep.get("caballos", "?") if rep else "?"
        cab_str = f"{c_plan}/{c_rep}"

        if par:
            todos_codigos = _codigos_carrera_par_laplata(ap_plan, ap_rep, pos_ap)
        else:
            todos_codigos = _ordenar_codigos(set(ap_plan.keys()) | set(ap_rep.keys()))
        for idx, cod in enumerate(todos_codigos):
            v_plan = ap_plan.get(cod)
            v_rep = ap_rep.get(cod)
            v_pos = pos_ap.get(cod) if incluir_posting_col else None
            if incluir_posting_col:
                estado = _estado_tres_fuentes(v_plan, v_rep, v_pos, "Planilla")
            else:
                estado = _estado_apuesta(v_plan, v_rep, "Planilla", "reporte")
            num_errores, num_avisos = _contar_fila_estado(estado, num_errores, num_avisos)

            if idx == 0 and num_carrera != todas[0]:
                t.add_section()

            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""
            celdas = [
                carrera_str, cab_show, f"[codigo]{cod}[/codigo]",
                _celda_valor_rich(v_plan, v_rep),
                _celda_valor_rich(v_rep, v_plan),
            ]
            if incluir_posting_col:
                celdas.append(_celda_valor_rich(v_pos, v_rep))
            celdas.append(estado)
            t.add_row(*celdas)

            fila = [carrera_str, cab_show, cod, formato_valor(v_plan), formato_valor(v_rep)]
            if incluir_posting_col:
                fila.append(formato_valor(v_pos))
            fila.append(_estado_plano(estado))
            filas_html.append(fila)

    bloque = BloqueComparacion(
        titulo=titulo, tabla=t, num_carreras=len(todas),
        num_errores=num_errores, num_avisos=num_avisos,
    )
    _registrar_seccion_html(
        html_buffer, titulo, nombres_cols, filas_html,
        html_col="izq" if datos_posting else None,
    )
    if imprimir:
        _imprimir_bloque_comparacion_desde_bloque(bloque)
    return bloque


def imprimir_tabla_posting_vs_reporte(
    datos_posting: tuple[dict, set[str]],
    datos_reporte: tuple[dict, set[str]],
    html_buffer: Optional[list[SeccionComparacionHtml]] = None,
    datos_fuente: Optional[dict] = None,
    datos_reporte_meta: Optional[dict] = None,
    label_fuente: Optional[str] = None,
    imprimir: bool = True,
    compacto: bool = False,
    par: bool = False,
) -> BloqueComparacion:
    valores_posting, _ = datos_posting
    valores_reporte, _ = datos_reporte
    fuente_flat = _apuestas_flat_por_carrera(datos_fuente) if datos_fuente else {}
    lbl = label_fuente or "OFICIAL"
    if datos_fuente:
        titulo = f"COMPARACION {lbl} · POSTING · REPORTE"
        columnas_def = _perfil_columnas_comparacion(
            lbl, con_posting=True, compacto=compacto, par=par,
        )
    else:
        titulo = "COMPARACION POSTING vs REPORTE"
        wv = _ancho_valor(compacto=compacto, par=par)
        wc = _ancho_carrera(compacto=compacto, par=par)
        wa = _ancho_apuesta(compacto=compacto, par=par)
        columnas_def = [
            ("Carr.", {"style": "carrera", "width": wc, "justify": "center"}),
            ("Ap.", {"style": "codigo", "width": wa, "min_width": wa, "no_wrap": True}),
            (_header_columna_posting(par=par), {"justify": "right", "width": wv}),
            (_header_columna_reporte(par=par), {"justify": "right", "width": wv}),
            ("Estado", _kwargs_col_estado(compacto=compacto, par=par)),
        ]
    t = _crear_tabla_comparacion(columnas_def, par=par, compacto=compacto)
    nombres_cols = [c[0] for c in columnas_def]
    filas_html: list[list[str]] = []
    num_errores = 0
    num_avisos = 0

    carreras_fuente = set(fuente_flat.keys()) if datos_fuente else set()
    todas = sorted(set(valores_posting.keys()) | set(valores_reporte.keys()) | carreras_fuente)
    for num_carrera in todas:
        pos_ap = valores_posting.get(num_carrera, {})
        rep_ap = valores_reporte.get(num_carrera, {})
        src_ap = fuente_flat.get(num_carrera, {}) if datos_fuente else {}
        if par and _es_fuente_planilla(lbl):
            codigos = _codigos_carrera_par_laplata(src_ap, rep_ap, pos_ap)
        else:
            codigos = _ordenar_codigos(set(pos_ap.keys()) | set(rep_ap.keys()) | set(src_ap.keys()))
        for idx, cod in enumerate(codigos):
            v_pos = pos_ap.get(cod)
            v_rep = rep_ap.get(cod)
            v_src = src_ap.get(cod) if datos_fuente else None
            if datos_fuente:
                estado = _estado_posting_triple(v_pos, v_src, v_rep, lbl)
            else:
                estado = _estado_apuesta(v_pos, v_rep, "posting", "reporte")
            num_errores, num_avisos = _contar_fila_estado(estado, num_errores, num_avisos)

            if idx == 0 and num_carrera != todas[0]:
                t.add_section()

            carrera_str = str(num_carrera) if idx == 0 else ""
            if datos_fuente:
                cab_show = _caballos_str(num_carrera, datos_fuente, datos_reporte_meta) if idx == 0 else ""
                celdas = [
                    carrera_str, cab_show, f"[codigo]{cod}[/codigo]",
                    _celda_valor_rich(v_src, v_rep),
                    _celda_valor_rich(v_rep, v_pos),
                    _celda_valor_rich(v_pos, v_rep),
                    estado,
                ]
                fila = [
                    carrera_str, cab_show, cod,
                    formato_valor(v_src), formato_valor(v_rep), formato_valor(v_pos),
                    _estado_plano(estado),
                ]
            else:
                celdas = [
                    carrera_str, f"[codigo]{cod}[/codigo]",
                    _celda_valor_rich(v_pos, v_rep),
                    _celda_valor_rich(v_rep, v_pos),
                    estado,
                ]
                fila = [carrera_str, cod, formato_valor(v_pos), formato_valor(v_rep), _estado_plano(estado)]
            t.add_row(*celdas)
            filas_html.append(fila)

    bloque = BloqueComparacion(
        titulo=titulo, tabla=t, num_carreras=len(todas),
        num_errores=num_errores, num_avisos=num_avisos,
    )
    _registrar_seccion_html(html_buffer, titulo, nombres_cols, filas_html, html_col="der")
    if imprimir:
        _imprimir_bloque_comparacion_desde_bloque(bloque)
    return bloque


def _validar_carreras_tela(datos: dict[int, dict]) -> dict[int, tuple[int, list[tuple[str, str]]]]:
    """Valida cada carrera. Retorna {carrera: (caballos, [(observación, regla), ...])}."""
    resultados: dict[int, tuple[int, list[tuple[str, str]]]] = {}
    for num_carrera in sorted(datos.keys()):
        d = datos[num_carrera]
        cab = d.get("caballos", 0)
        apuestas = set(d.get("apuestas", {}).keys())
        violaciones: list[tuple[str, str]] = []

        if cab < 8 and "TER" in apuestas:
            violaciones.append(("TER no debería estar", "< 8 caballos → sin TER"))

        if cab >= 12:
            if "IMP" not in apuestas:
                violaciones.append(("IMP debería estar", "≥ 12 caballos → IMP obligatorio"))
            if "EXA" in apuestas:
                violaciones.append(("EXA no debería estar", "≥ 12 caballos → sin EXA"))

        if cab <= 11:
            if "EXA" not in apuestas:
                violaciones.append(("EXA debería estar", "≤ 11 caballos → EXA obligatorio"))
            if "IMP" in apuestas:
                violaciones.append(("IMP no debería estar", "≤ 11 caballos → sin IMP"))

        if cab == 4:
            if "SEG" in apuestas:
                violaciones.append(("SEG no debería estar", "4 caballos → sin SEG/TRI/CUA"))
            if "TRI" in apuestas:
                violaciones.append(("TRI no debería estar", "4 caballos → sin SEG/TRI/CUA"))
            if "CUA" in apuestas:
                violaciones.append(("CUA no debería estar", "4 caballos → sin SEG/TRI/CUA"))

        if "EXA" in apuestas and "IMP" in apuestas:
            violaciones.append((MSG_EXA_IMP_JUNTOS, MSG_EXA_IMP_JUNTOS))

        if "TRI" in apuestas and "CUA" in apuestas:
            violaciones.append((MSG_TRI_CUA_JUNTOS, MSG_TRI_CUA_JUNTOS))

        picks = [cod for cod in apuestas if cod in APUESTAS_PICK]
        if len(picks) > 1:
            violaciones.append((
                f"apuestas pick conflictivas ({', '.join(picks)})",
                "Una sola pick por carrera (TPL/QTN/QTP/CAD)",
            ))

        resultados[num_carrera] = (cab, violaciones)

    return resultados


MSG_EXA_IMP_JUNTOS = "EXA e IMP no pueden estar juntas"
MSG_TRI_CUA_JUNTOS = "TRI y CUA no pueden estar juntas"

_REGLAS_CABALLOS_VALIDACION_TELA: tuple[str, ...] = (
    "< 8 caballos → sin TER",
    "≤ 11 caballos → EXA obligatorio",
    "≤ 11 caballos → sin IMP",
    "≥ 12 caballos → IMP obligatorio",
    "≥ 12 caballos → sin EXA",
    "4 caballos → sin SEG/TRI/CUA",
)

_REGLAS_PARES_VALIDACION_TELA: tuple[str, str] = (
    MSG_EXA_IMP_JUNTOS,
    MSG_TRI_CUA_JUNTOS,
)

_REGLA_PICK_VALIDACION_TELA = "Una sola pick por carrera (TPL/QTN/QTP/CAD)"

_REGLAS_VALIDACION_TELA: tuple[str, ...] = (
    *_REGLAS_CABALLOS_VALIDACION_TELA,
    _REGLA_PICK_VALIDACION_TELA,
)


def _render_panel_reglas_validacion() -> Group:
    lineas = [f"• {regla}" for regla in _REGLAS_CABALLOS_VALIDACION_TELA]
    lineas.append(f"• {_REGLA_PICK_VALIDACION_TELA}")
    pares = Table(box=None, show_header=False, pad_edge=False, expand=True)
    pares.add_column(ratio=1)
    pares.add_column(ratio=1)
    pares.add_row(_REGLAS_PARES_VALIDACION_TELA[0], _REGLAS_PARES_VALIDACION_TELA[1])
    return Group("\n".join(lineas), "", pares)


_ANCHO_VALIDACIONES_TABLA = 54
_ANCHO_VALIDACIONES_REGLAS = 46


def _tabla_validaciones_carreras(
    resultados: dict[int, tuple[int, list[tuple[str, str]]]],
) -> Table:
    t = Table(box=box.SIMPLE, header_style="bold", expand=False)
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Observación", width=36)
    for num_carrera in sorted(resultados.keys()):
        cab, violaciones = resultados[num_carrera]
        if not violaciones:
            obs = "[green]OK[/green]"
        else:
            obs = " / ".join(obs for obs, _ in violaciones)
            obs = f"[yellow]{obs}[/yellow]"
        t.add_row(str(num_carrera), str(cab), obs)
    return t


def _panel_reglas_validacion() -> Panel:
    return Panel(
        _render_panel_reglas_validacion(),
        border_style="dim",
        padding=(0, 1),
        width=_ANCHO_VALIDACIONES_REGLAS,
    )


def _mostrar_validaciones(resultados: dict[int, tuple[int, list[tuple[str, str]]]]) -> None:
    tabla = _tabla_validaciones_carreras(resultados)
    panel_reglas = _panel_reglas_validacion()
    ancho_izq = _ANCHO_VALIDACIONES_TABLA
    ancho_der = _ANCHO_VALIDACIONES_REGLAS
    tit_izq = _titulo_par_texto("VALIDACIONES", ancho_izq)
    tit_der = _titulo_par_texto("Reglas validadas", ancho_der)
    _imprimir_renderables_pegados(tit_izq, tit_der, ancho_izq, ancho_der, ancho_fijo=True)
    _imprimir_renderables_pegados(tabla, panel_reglas, ancho_izq, ancho_der)
    console.print()


def _html_validaciones_tela(resultados: dict[int, tuple[int, list[tuple[str, str]]]]) -> str:
    """Tabla HTML de validaciones tela oficial."""
    html = '<div class="validaciones-row">\n'
    html += '<div class="col-panel">\n'
    html += '<div class="subtitle">VALIDACIONES</div>\n'
    html += '<table class="validaciones-table">\n<thead><tr>'
    html += "<th>Carrera</th><th>Caballos</th><th>Observación</th>"
    html += "</tr></thead>\n<tbody>\n"
    for num_carrera in sorted(resultados.keys()):
        cab, violaciones = resultados[num_carrera]
        if not violaciones:
            html += (
                f"<tr><td>{num_carrera}</td><td class=\"center\">{cab}</td>"
                f"<td class=\"ok\">OK</td></tr>\n"
            )
        else:
            obs = " / ".join(obs for obs, _ in violaciones)
            html += (
                f"<tr><td>{num_carrera}</td><td class=\"center\">{cab}</td>"
                f"<td class=\"warn\">{obs}</td></tr>\n"
            )
    html += "</tbody></table>\n</div>\n"
    html += '<div class="col-panel validaciones-reglas-panel">\n'
    html += '<div class="subtitle">Reglas validadas</div>\n'
    html += '<div class="validaciones-reglas"><ul>\n'
    for regla in _REGLAS_VALIDACION_TELA:
        html += f"<li>{regla}</li>\n"
    html += "</ul>\n"
    html += '<table class="validaciones-pares-table"><tr>'
    html += f"<td>{_REGLAS_PARES_VALIDACION_TELA[0]}</td>"
    html += f"<td>{_REGLAS_PARES_VALIDACION_TELA[1]}</td>"
    html += "</tr></table></div>\n</div>\n</div>\n"
    return html


def _format_carreras_list(carreras: list[int], total: int, cod: str | None = None) -> str:
    if len(carreras) == total and cod in APUESTAS_CARRERAS_ALL:
        return "ALL"
    carreras = sorted(carreras)
    ranges: list[str] = []
    start = carreras[0]
    end = carreras[0]
    for c in carreras[1:]:
        if c == end + 1:
            end = c
        else:
            ranges.append(f"{start}" if start == end else f"{start}-{end}")
            start = c
            end = c
    ranges.append(f"{start}" if start == end else f"{start}-{end}")
    return ",".join(ranges)


def _agrupar_bases_por_apuesta(datos: dict[int, dict]) -> dict[tuple[str, float | None], list[int]]:
    """Agrupa carreras por (código, valor) — misma fuente que la tabla BASES POR APUESTA."""
    grupos: dict[tuple[str, float | None], list[int]] = {}
    for num_carrera in sorted(datos.keys()):
        for cod, val in datos[num_carrera].get("apuestas", {}).items():
            if cod in ("GAN", "SEG", "TER"):
                continue
            grupos.setdefault((cod, val), []).append(num_carrera)
    return grupos


def _texto_resumen_base_unica(carreras: list[int], cod: str, val: float) -> str:
    """Un solo valor base en la reunión: 'unica' si es 1 carrera, 'todas' si son 2+."""
    if len(carreras) > 1:
        return f"{cod}: todas son de {formato_valor(val)}"
    return f"{cod}: unica de {formato_valor(val)}"


def _mostrar_bases_por_apuesta(datos: dict[int, dict]) -> None:
    grupos = _agrupar_bases_por_apuesta(datos)
    total = len(datos)
    codes = _ordenar_codigos({cod for cod, _ in grupos.keys()})

    ordered: list[tuple[tuple[str, float | None], list[int]]] = []
    for cod in codes:
        entries = [(v, carreras) for (c, v), carreras in grupos.items() if c == cod]
        entries.sort(key=lambda x: (0, x[0]) if x[0] is not None else (1, 0))
        for val, carreras in entries:
            ordered.append(((cod, val), carreras))

    t = Table(box=box.SIMPLE, header_style="bold", title="[bold]BASES POR APUESTA[/bold]")
    t.add_column("#", justify="right", width=3, style="dim")
    t.add_column("Carreras", width=16)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column("Base", justify="right", width=10)

    for idx, ((cod, val), carreras) in enumerate(ordered, 1):
        t.add_row(str(idx), _format_carreras_list(carreras, total, cod), cod, formato_valor(val))

    console.print(t)
    console.print()


def _agrupar_pases_por_secuencia(datos: dict[int, dict]) -> dict[str, list[tuple[int, int, str, str]]]:
    """Analiza pases y retorna {codigo: [(carrera_inicio, carrera_fin, detalle, estado)]}
    usando lógica de secuencia: 1er.Pase en C1 → 2do.Pase en C2 → ..."""
    triples: list[tuple[int, str, str]] = []
    for num_carrera in sorted(datos.keys()):
        d = datos[num_carrera]
        pases = d.get("pases")
        if not pases:
            continue
        for codigo, pases_set in pases.items():
            for pase in pases_set:
                triples.append((num_carrera, codigo, pase))

    lookup: set[tuple[int, str, str]] = set(triples)

    starts: dict[str, list[int]] = {}
    for c, co, p in triples:
        if p == "1er.Pase":
            starts.setdefault(co, []).append(c)
    for co in starts:
        starts[co].sort()

    resultado: dict[str, list[tuple[int, int, str, str]]] = {}
    for codigo in sorted(starts.keys()):
        expected = PASES_POR_APUESTA.get(codigo)
        if not expected:
            continue
        secuencias: list[tuple[int, int, str, str]] = []
        for sc in starts[codigo]:
            partes: list[str] = []
            faltantes: list[str] = []
            for idx, pase_name in enumerate(expected):
                carrera = sc + idx
                if (carrera, codigo, pase_name) in lookup:
                    partes.append(f"{pase_name}(C{carrera})")
                else:
                    faltantes.append(pase_name)
            fin = sc + len(expected) - 1
            if faltantes:
                detalle = f"Falta: {', '.join(faltantes)}"
                estado = "[yellow]INCOMPLETA[/yellow]"
            else:
                detalle = " → ".join(partes)
                estado = "[green]COMPLETA[/green]"
            secuencias.append((sc, fin, detalle, estado))
        if secuencias:
            resultado[codigo] = secuencias
    return resultado


def _mostrar_validacion_pases(datos: dict[int, dict]) -> None:
    secuencias = _agrupar_pases_por_secuencia(datos)
    if not secuencias:
        return

    console.print()
    for codigo in sorted(secuencias.keys()):
        seqs = secuencias[codigo]
        expected = PASES_POR_APUESTA.get(codigo, [])
        t = Table(
            box=box.SIMPLE, header_style="bold",
            title=f"[bold]CONTROL DE PASES - {codigo} ({len(expected)}p)[/bold]",
        )
        t.add_column("#", justify="right", width=3, style="dim")
        t.add_column("Carreras", width=12)
        t.add_column("Detalle", width=75)
        t.add_column("Estado", justify="center", width=14)

        for i, (sc, fin, detalle, estado) in enumerate(seqs, 1):
            t.add_row(str(i), f"C{sc}→C{fin}", detalle, estado)

        console.print(t)
        console.print()


def _mostrar_resumen_bases_unicas(datos: dict[int, dict]) -> None:
    from collections import defaultdict
    valores_por_codigo: dict[str, set[float | None]] = defaultdict(set)
    for d in datos.values():
        apuestas = d.get("apuestas", {})
        for cod, val in apuestas.items():
            if cod in ("GAN", "SEG", "TER"):
                continue
            valores_por_codigo[cod].add(val)

    lineas: list[str] = []
    grupos = _agrupar_bases_por_apuesta(datos)
    for cod in sorted(valores_por_codigo.keys()):
        vals = valores_por_codigo[cod]
        if len(vals) == 1:
            val = next(iter(vals))
            if val is not None:
                carreras = grupos.get((cod, val), [])
                lineas.append(_texto_resumen_base_unica(carreras, cod, val))

    if not lineas:
        return

    console.print()
    for linea in lineas:
        console.print(f"  [red]{linea}[/red]")
    console.print()


def imprimir_resumen_tela(datos: dict[int, dict], ruta: str) -> None:
    console.print(f"  [dim]Archivo:[/dim] {ruta}")
    _mostrar_bases_por_apuesta(datos)
    _mostrar_resumen_bases_unicas(datos)
    resultados = _validar_carreras_tela(datos)
    _mostrar_validaciones(resultados)
    _mostrar_validacion_pases(datos)


def exportar_resumen_html(datos: dict[int, dict], ruta_pdf: str | Path, ruta_salida: str | Path) -> None:
    info = extraer_info_reunion_tela(ruta_pdf)
    grupos = _agrupar_bases_por_apuesta(datos)
    total = len(datos)
    codes = _ordenar_codigos({cod for cod, _ in grupos.keys()})

    filas: list[tuple[str, str, str]] = []
    for cod in codes:
        entries = [(v, carreras) for (c, v), carreras in grupos.items() if c == cod]
        entries.sort(key=lambda x: (0, x[0]) if x[0] is not None else (1, 0))
        for val, carreras in entries:
            if len(entries) == 1 and cod in APUESTAS_CARRERAS_ALL:
                carrera_str = "ALL"
            else:
                carrera_str = _format_carreras_list(carreras, total, cod)
            filas.append((carrera_str, cod, formato_valor(val)))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts_file = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    header = f"Reunión {info['reunion']} — {info['fecha']} — {info['hipodromo']}" if info.get("reunion") else "Tela Oficial"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">

<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    padding: 15px;
    background: #fff;
    color: #333;
  }}
  .container {{
    width: fit-content;
    max-width: 100%;
    border: 1px solid #c8e6c9;
    border-radius: 6px;
    overflow: hidden;
  }}
  .header {{
    background: #1b5e20;
    color: #fff;
    padding: 10px 14px;
  }}
  .header h1 {{ font-size: 14px; font-weight: 600; }}
  .subtitle {{
    font-size: 12px;
    font-weight: 600;
    color: #2e7d32;
    padding: 8px 14px 4px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th {{
    background: #1b5e20;
    color: #fff;
    padding: 5px 10px;
    text-align: left;
    font-weight: 600;
  }}
  .bases-table th:nth-child(1) {{ width: 50%; }}
  .bases-table th:nth-child(2) {{ width: 20%; }}
  .bases-table th:nth-child(3) {{ width: 30%; }}
  .validaciones-table th:nth-child(1) {{ width: 10%; }}
  .validaciones-table th:nth-child(2) {{ width: 12%; }}
  .validaciones-table th:nth-child(3) {{ width: 78%; }}
  .validaciones-row {{
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 0 14px 10px;
  }}
  .validaciones-row .col-panel {{
    flex: 1;
    min-width: 0;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
  }}
  .validaciones-row .col-panel .subtitle {{
    margin: 0;
  }}
  .validaciones-reglas-panel .validaciones-reglas {{
    padding: 4px 10px 10px;
  }}
  .validaciones-reglas {{
    font-size: 12px;
    color: #555;
    padding: 4px 14px 10px;
  }}
  .validaciones-reglas ul {{
    margin: 4px 0 0 18px;
    padding: 0;
  }}
  .validaciones-reglas li {{
    margin: 2px 0;
  }}
  .validaciones-pares-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    color: #555;
    margin-top: 6px;
  }}
  .validaciones-pares-table td {{
    width: 50%;
    padding: 2px 0;
    vertical-align: top;
  }}
  td.center {{ text-align: center; }}
  .pases-table th:nth-child(1) {{ width: 5%; }}
  .pases-table th:nth-child(2) {{ width: 15%; }}
  .pases-table th:nth-child(3) {{ width: 62%; }}
  .pases-table th:nth-child(4) {{ width: 18%; }}
  th.right {{ text-align: right; }}
  td {{
    padding: 3px 10px;
    border-bottom: 1px solid #e0e0e0;
  }}
  td.dim {{ color: #999; }}
  td.right {{ text-align: right; }}
  td.bet {{ color: #2e7d32; font-weight: 600; }}
  td.ok {{ color: #2e7d32; font-weight: 600; }}
  td.warn {{ color: #e65100; font-weight: 600; }}
  .resumen-line {{
    font-size: 12px;
    padding: 2px 14px;
    color: #c62828;
    font-weight: 600;
  }}
  tr:nth-child(even) {{ background: #f1f8e9; }}
  tr:nth-child(odd) {{ background: #fff; }}
  @media print {{
    body {{ padding: 10px; }}
    .container {{ border: 1px solid #c8e6c9; }}
    .header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tr:nth-child(even) {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>{header}</h1></div>
<div class="subtitle">BASES POR APUESTA</div>
<table class="bases-table">
<thead>
<tr><th>Carreras</th><th>Apuesta</th><th class="right">Base</th></tr>
</thead>
<tbody>
"""
    for carreras, cod, val in filas:
        html += f"<tr><td>{carreras}</td><td class=\"bet\">{cod}</td><td class=\"right\">{val}</td></tr>\n"

    html += """</tbody>
</table>
"""

    # --- Resumen de bases únicas ---
    from collections import defaultdict
    valores_por_codigo: dict[str, set[float | None]] = defaultdict(set)
    for d in datos.values():
        apuestas = d.get("apuestas", {})
        for cod, val in apuestas.items():
            if cod in ("GAN", "SEG", "TER"):
                continue
            valores_por_codigo[cod].add(val)

    resumen_lineas: list[str] = []
    for cod in sorted(valores_por_codigo.keys()):
        vals = valores_por_codigo[cod]
        if len(vals) == 1:
            val = next(iter(vals))
            if val is not None:
                carreras = grupos.get((cod, val), [])
                texto = _texto_resumen_base_unica(carreras, cod, val)
                resumen_lineas.append(f"<span class=\"resumen-base\">{texto}</span>")

    if resumen_lineas:
        for linea in resumen_lineas:
            html += f'<div class="resumen-line">{linea}</div>\n'

    # --- Validaciones por carrera ---
    resultados_val = _validar_carreras_tela(datos)
    html += _html_validaciones_tela(resultados_val)

    # --- Tabla de pases (secuencias) ---
    secuencias = _agrupar_pases_por_secuencia(datos)
    if secuencias:
        html += '<div class="subtitle">CONTROL DE PASES</div>\n'
        for codigo in sorted(secuencias.keys()):
            seqs = secuencias[codigo]
            expected = PASES_POR_APUESTA.get(codigo, [])
            html += f'<table class="pases-table" style="margin-bottom:8px">\n'
            html += f'<thead>\n'
            html += f'<tr><th colspan="4" style="text-align:center">CONTROL DE PASES - {codigo} ({len(expected)}p)</th></tr>\n'
            html += f'<tr><th>#</th><th>Carreras</th><th>Detalle</th><th class="right">Estado</th></tr>\n'
            html += f'</thead>\n<tbody>\n'
            for i, (sc, fin, detalle, estado) in enumerate(seqs, 1):
                is_ok = "COMPLETA" in estado
                estado_class = "ok" if is_ok else "warn"
                estado_clean = "COMPLETA" if is_ok else "INCOMPLETA"
                html += f'<tr><td>{i}</td><td>C{sc}→C{fin}</td><td>{detalle}</td><td class="right {estado_class}">{estado_clean}</td></tr>\n'
            html += '</tbody>\n</table>\n'

    html += """</div>
</body>
</html>"""

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)


def _html_tabla_seccion(seccion: SeccionComparacionHtml, wrap_col: bool = False) -> str:
    titulo = seccion.get("titulo", "Comparación")
    columnas = seccion.get("columnas", [])
    filas = seccion.get("filas", [])
    prefix = '<div class="col-panel">' if wrap_col else ""
    suffix = "</div>" if wrap_col else ""
    html = prefix + f'<div class="subtitle">{titulo}</div>\n<table>\n<thead><tr>\n'
    for col in columnas:
        th_cls, _ = _html_clases_columna(col)
        cls_attr = f' class="{th_cls}"' if th_cls else ""
        html += f"<th{cls_attr}>{col}</th>"
    html += "</tr></thead>\n<tbody>\n"
    prev_carrera = None
    for fila in filas:
        carrera_cel = fila[0] if fila else ""
        tr_cls = ' class="carrera-start"' if carrera_cel and carrera_cel != prev_carrera and prev_carrera is not None else ""
        prev_carrera = carrera_cel or prev_carrera
        html += f"<tr{tr_cls}>"
        for i, celda in enumerate(fila):
            col = columnas[i] if i < len(columnas) else ""
            _, base_cls = _html_clases_columna(col)
            td_cls = ""
            if col == "Ap." or col == "Apuesta":
                td_cls = ' class="bet"'
            elif col == "Estado":
                texto = str(celda)
                if SYM_OK in texto:
                    td_cls = ' class="center ok"'
                elif SYM_FAIL in texto:
                    td_cls = ' class="center diff"'
                elif "no en " in texto.lower():
                    td_cls = ' class="center warn"'
                else:
                    td_cls = ' class="center"'
            elif celda == "-":
                td_cls = f' class="dim {base_cls}"' if base_cls else ' class="dim"'
            elif base_cls:
                td_cls = f' class="{base_cls}"'
            html += f"<td{td_cls}>{celda}</td>"
        html += "</tr>\n"
    html += f"</tbody></table>\n{suffix}"
    return html


def exportar_comparacion_html(
    secciones: list[SeccionComparacionHtml],
    ruta_salida: str | Path,
    titulo_doc: str = "ControlComparador — Comparación",
    meta_lineas: Optional[list[str]] = None,
    diferencias: Optional[list[tuple[str, list[str]]]] = None,
) -> None:
    """Genera HTML con todas las tablas de comparación (misma data que consola)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_html = "".join(f'<div class="meta">{line}</div>' for line in (meta_lineas or []))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{titulo_doc}</title>
<style>{_HTML_CSS_COMPARACION}</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>{titulo_doc}</h1>
  {meta_html}
  <div class="meta">Generado: {ts}</div>
</div>
"""

    i = 0
    while i < len(secciones):
        sec = secciones[i]
        col = sec.get("html_col")
        if col == "izq" and i + 1 < len(secciones) and secciones[i + 1].get("html_col") == "der":
            html += '<div class="two-col-row">\n'
            html += _html_tabla_seccion(sec, wrap_col=True)
            html += _html_tabla_seccion(secciones[i + 1], wrap_col=True)
            html += "</div>\n"
            i += 2
        else:
            html += _html_tabla_seccion(sec, wrap_col=False)
            i += 1

    hay_diffs = any(items for _, items in (diferencias or []))
    if hay_diffs:
        html += '<div class="subtitle">DIFERENCIAS DETECTADAS</div>\n<ul class="diff-list">\n'
        for titulo_diff, items in diferencias:
            if items:
                html += f"<li><strong>{titulo_diff}</strong></li>\n"
                for item in items:
                    html += f"<li>{item}</li>\n"
        html += "</ul>\n"

    html += "</div>\n</body>\n</html>"

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)


def ofrecer_export_comparacion_html(
    secciones: list[SeccionComparacionHtml],
    hipodromo: str,
    diferencias: Optional[list[tuple[str, list[str]]]] = None,
    meta_lineas: Optional[list[str]] = None,
    ruta_salida: Optional[Path] = None,
) -> Optional[Path]:
    """Si hay secciones, exporta HTML al Escritorio o ruta indicada. Retorna ruta o None."""
    import os
    from rich.prompt import Confirm

    if not secciones:
        return None
    if ruta_salida is None:
        if not Confirm.ask("¿Guardar comparación como HTML?", default=False):
            return None
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        ruta_salida = Path(os.path.expanduser("~/Desktop")) / f"ControlComparador_{hipodromo}_{ts}.html"
    exportar_comparacion_html(
        secciones,
        ruta_salida,
        titulo_doc=f"ControlComparador — {hipodromo.replace('_', ' ').title()}",
        meta_lineas=meta_lineas,
        diferencias=diferencias,
    )
    return ruta_salida


def mostrar_resumen_comparacion(coincide: bool, diferencias: list[str], titulo: str = "COMPARACION") -> None:
    if coincide:
        console.print(Panel(
            f"{SYM_OK} Todo coincide correctamente.",
            title=titulo,
            border_style="#2e7d32",
            style="ok",
        ))
    else:
        cuerpo = "\n".join(f"• {d}" for d in diferencias)
        console.print(Panel(
            cuerpo,
            title=f"{SYM_FAIL} {titulo}",
            border_style="red",
            style="warn",
        ))
    console.print()


def mostrar_resumenes_consolidado(
    checks: list[tuple[str, bool, list[str]]],
    titulo_panel: str = "RESUMEN COMPARACIONES",
) -> None:
    """Un solo panel con todas las comparaciones (evita resúmenes sueltos y tardíos)."""
    lineas: list[str] = []
    hay_error = False
    for nombre, coincide, diferencias in checks:
        if coincide:
            lineas.append(f"[ok]{SYM_OK}[/ok] {nombre}")
        else:
            hay_error = True
            lineas.append(f"[fail]{SYM_FAIL}[/fail] {nombre}")
            for d in diferencias:
                lineas.append(f"  • {d}")
    console.print(Panel(
        "\n".join(lineas),
        title=f"[bold]{titulo_panel}[/bold]",
        border_style="red" if hay_error else "#2e7d32",
    ))
    console.print()



