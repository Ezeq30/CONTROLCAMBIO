# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import typer
import os as _os
from datetime import datetime
from rich.prompt import Prompt, Confirm

from controlcomparador import __version__
from controlcomparador.agent import AgenteComparacion
from controlcomparador.detector import detectar_archivos, hipodromos_detectados, resumen_deteccion
from controlcomparador.parsers.pdf import es_tela_oficial, obtener_apuestas_por_carrera, normalizar_desde_lista_apuestas, extraer_pases_tela_oficial
from controlcomparador.parsers.report import normalizar_reporte_palermo
from controlcomparador.ui.console import console
from controlcomparador.ui.tables import (
    exportar_resumen_html,
    imprimir_tabla_san_isidro,
    imprimir_tablas_palermo,
    imprimir_tabla_laplata,
    imprimir_tabla_posting_vs_reporte,
    imprimir_par_comparacion,
    imprimir_resumen_tela,
    mostrar_resumen_comparacion,
    mostrar_resumenes_consolidado,
    ofrecer_export_comparacion_html,
    SeccionComparacionHtml,
    BloqueComparacion,
)
from controlcomparador.control_xml import controlar_xml, imprimir_control_xml
from controlcomparador.ui.menus import (
    menu_principal,
    menu_auto_detect,
    limpiar_pantalla,
    seleccionar_archivo,
    seleccionar_carpeta,
    mostrar_menu_archivos,
)

app = typer.Typer(
    name="controlcomparador",
    help="ControlComparador - Comparacion de archivos hipicos",
    add_completion=False,
)

_agente = AgenteComparacion()


def _exportar_html_si_corresponde(
    html_buffer: list[SeccionComparacionHtml],
    hipodromo: str,
    diferencias: list[tuple[str, list[str]]],
    meta_lineas: list[str],
    ruta_html: Optional[Path] = None,
    preguntar: bool = True,
) -> None:
    if not html_buffer:
        return
    if ruta_html is not None:
        from controlcomparador.ui.tables import exportar_comparacion_html
        exportar_comparacion_html(
            html_buffer,
            ruta_html,
            titulo_doc=f"ControlComparador — {hipodromo.replace('_', ' ').title()}",
            meta_lineas=meta_lineas,
            diferencias=diferencias,
        )
        console.print(f"[green]HTML guardado en:[/green] {ruta_html}")
        _os.startfile(ruta_html)
        return
    if not preguntar:
        return
    ruta = ofrecer_export_comparacion_html(
        html_buffer, hipodromo, diferencias=diferencias, meta_lineas=meta_lineas,
    )
    if ruta:
        console.print(f"[green]HTML guardado en:[/green] {ruta}")
        _os.startfile(ruta)


def _imprimir_comparacion_con_posting(
    bloque_izq: BloqueComparacion,
    resultado_posting: dict,
    ruta_reporte: str | Path,
    html_buffer: Optional[list[SeccionComparacionHtml]] = None,
    datos_fuente: Optional[dict] = None,
    datos_reporte_meta: Optional[dict] = None,
    label_fuente: Optional[str] = None,
) -> str:
    """Vista par: tabla principal (izq) + posting triple (der) vía ``imprimir_par_comparacion``."""
    datos_reporte = normalizar_reporte_palermo(ruta_reporte)
    bloque_der = imprimir_tabla_posting_vs_reporte(
        resultado_posting["datos_posting"],
        datos_reporte,
        html_buffer=html_buffer,
        datos_fuente=datos_fuente,
        datos_reporte_meta=datos_reporte_meta,
        label_fuente=label_fuente,
        imprimir=False,
        compacto=True,
        par=True,
    )
    imprimir_par_comparacion(bloque_izq, bloque_der)
    return bloque_der.titulo


def _mostrar_resumenes_palermo_posting(
    diffs: list[tuple[str, list[str]]],
    *,
    coincide_bases: bool,
    diferencias_bases: list[str],
    titulo_bases: str = "PALERMO BASES vs REPORTE",
    coincide_oficial: Optional[bool] = None,
    diferencias_oficial: Optional[list[str]] = None,
    resultado_posting: Optional[dict] = None,
    label_fuente: str = "Bases Palermo",
    vista_par: bool = False,
) -> None:
    checks: list[tuple[str, bool, list[str]]] = [
        (titulo_bases, coincide_bases, diferencias_bases),
    ]
    if coincide_oficial is not None and diferencias_oficial is not None:
        checks.append(("OFICIAL vs REPORTE", coincide_oficial, diferencias_oficial))
    if resultado_posting is not None:
        titulo_post = f"{label_fuente} · POSTING · REPORTE"
        checks.append((
            titulo_post,
            resultado_posting["coincide"],
            resultado_posting["diferencias"],
        ))
    for nombre, _, diferencias in checks:
        diffs.append((nombre, diferencias))
    if vista_par:
        fallos = [(n, c, d) for n, c, d in checks if not c]
        if fallos:
            mostrar_resumenes_consolidado(fallos, titulo_panel="DIFERENCIAS DETECTADAS")
        return
    for nombre, coincide, diferencias in checks:
        mostrar_resumen_comparacion(coincide, diferencias, nombre)


def _con_posting(posting, resultado_posting) -> bool:
    return bool(posting and resultado_posting)


def _mostrar_resumenes_posting(
    label_fuente: str,
    resultado_fuente: dict,
    resultado_posting: dict,
    diffs: list[tuple[str, list[str]]],
    *,
    vista_par: bool = False,
) -> None:
    """Registra difs; en vista par solo muestra panel consolidado si hay fallos."""
    label = f"{label_fuente} vs REPORTE"
    titulo_post = f"{label_fuente} · POSTING · REPORTE"
    checks = [
        (label, resultado_fuente["coincide"], resultado_fuente["diferencias"]),
        (titulo_post, resultado_posting["coincide"], resultado_posting["diferencias"]),
    ]
    for nombre, _, diferencias in checks:
        diffs.append((nombre, diferencias))
    if vista_par:
        fallos = [(n, c, d) for n, c, d in checks if not c]
        if fallos:
            mostrar_resumenes_consolidado(fallos, titulo_panel="DIFERENCIAS DETECTADAS")
        return
    for nombre, coincide, diferencias in checks:
        mostrar_resumen_comparacion(coincide, diferencias, nombre)


@app.command()
def version():
    """Muestra la version del programa."""
    console.print(f"[bold]ControlComparador[/bold] v{__version__}")


@app.command()
def san_isidro(
    pdf: Path = typer.Argument(..., help="Ruta al PDF del programa oficial", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
    html: Optional[Path] = typer.Option(None, "--html", help="Exportar comparacion completa a HTML", dir_okay=False, resolve_path=True),
):
    """Compara PDF vs Reporte para SAN ISIDRO."""
    html_buffer: list[SeccionComparacionHtml] = []
    diffs: list[tuple[str, list[str]]] = []
    meta = [f"PDF: {pdf.name}", f"Reporte: {reporte.name}"]

    with console.status("[bold blue]Comparando San Isidro...[/bold blue]"):
        resultado = _agente.comparar_san_isidro(pdf, reporte)
    meta.append(f"Tipo PDF: {resultado.get('tipo_pdf', 'OFICIAL')}")

    datos_posting = None
    resultado_posting = None
    if posting:
        meta.append(f"Posting: {', '.join(p.name for p in posting)}")
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting = resultado_posting["datos_posting"]

    par_posting = _con_posting(posting, resultado_posting)
    bloque = imprimir_tabla_san_isidro(
        resultado["datos_pdf"], resultado["datos_reporte"], datos_posting,
        resultado.get("fecha_reporte"), resultado.get("tipo_pdf"), html_buffer=html_buffer,
        imprimir=not par_posting,
        compacto=par_posting,
        par=par_posting,
    )
    if par_posting:
        _imprimir_comparacion_con_posting(
            bloque, resultado_posting, reporte, html_buffer,
            datos_fuente=resultado["datos_pdf"],
            datos_reporte_meta=resultado["datos_reporte"],
            label_fuente=resultado.get("tipo_pdf", "OFICIAL"),
        )
        _mostrar_resumenes_posting(
            resultado.get("tipo_pdf", "OFICIAL"), resultado, resultado_posting, diffs,
            vista_par=True,
        )
    else:
        label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
        diffs.append((label, resultado["diferencias"]))

    _exportar_html_si_corresponde(html_buffer, "san_isidro", diffs, meta, ruta_html=html, preguntar=html is None)


@app.command()
def palermo(
    bases: Path = typer.Argument(..., help="Ruta al PDF de Bases y Apuestas Palermo", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    oficial: Optional[Path] = typer.Option(None, "--oficial", "-o", help="Ruta al PDF oficial Palermo", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
    fecha: Optional[str] = typer.Option(None, "--fecha", "-f", help="Fecha objetivo (dd/mm/aaaa)"),
    html: Optional[Path] = typer.Option(None, "--html", help="Exportar comparacion completa a HTML", dir_okay=False, resolve_path=True),
):
    """Compara PDF vs Reporte para PALERMO."""
    html_buffer: list[SeccionComparacionHtml] = []
    diffs: list[tuple[str, list[str]]] = []
    meta = [f"Bases: {bases.name}", f"Reporte: {reporte.name}"]
    if oficial:
        meta.append(f"Oficial: {oficial.name}")
    if fecha:
        meta.append(f"Fecha: {fecha}")

    datos_posting = None
    resultado_posting = None
    if posting:
        meta.append(f"Posting: {', '.join(p.name for p in posting)}")
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting = resultado_posting["datos_posting"]

    datos_fuente_posting: Optional[dict] = None
    label_fuente_posting = "Bases Palermo"
    par_posting = _con_posting(posting, resultado_posting)
    bloque_palermo: Optional[BloqueComparacion] = None

    if oficial:
        with console.status("[bold blue]Comparando Palermo (completo)...[/bold blue]"):
            resultado = _agente.comparar_palermo_con_oficial(bases, reporte, oficial, fecha_objetivo=fecha)
        resultados_pal = resultado["palermo_vs_reporte"]
        resultados_of = resultado["oficial_vs_reporte"]
        datos_fuente_posting = resultados_pal["datos_pdf"]
        bloque_palermo = imprimir_tablas_palermo(
            resultados_pal["datos_pdf"],
            resultados_pal["datos_reporte"],
            resultados_pal.get("fechas_detectadas", []),
            resultados_pal.get("fecha_usada"),
            datos_posting=datos_posting,
            html_buffer=html_buffer,
            imprimir=not par_posting,
            compacto=par_posting,
            par=par_posting,
        )
        if not par_posting:
            mostrar_resumen_comparacion(resultados_pal["coincide"], resultados_pal["diferencias"], "PALERMO BASES vs REPORTE")
            diffs.append(("PALERMO BASES vs REPORTE", resultados_pal["diferencias"]))
            mostrar_resumen_comparacion(resultados_of["coincide"], resultados_of["diferencias"], "OFICIAL vs REPORTE")
            diffs.append(("OFICIAL vs REPORTE", resultados_of["diferencias"]))
    else:
        with console.status("[bold blue]Comparando Palermo (bases)...[/bold blue]"):
            resultado = _agente.comparar_palermo(bases, reporte, fecha_objetivo=fecha)
        datos_fuente_posting = resultado["datos_pdf"]
        bloque_palermo = imprimir_tablas_palermo(
            resultado["datos_pdf"],
            resultado["datos_reporte"],
            resultado.get("fechas_detectadas", []),
            resultado.get("fecha_usada"),
            datos_posting=datos_posting,
            html_buffer=html_buffer,
            imprimir=not par_posting,
            compacto=par_posting,
            par=par_posting,
        )
        if not par_posting:
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")
            diffs.append(("PALERMO vs REPORTE", resultado["diferencias"]))

    if par_posting and bloque_palermo is not None:
        _imprimir_comparacion_con_posting(
            bloque_palermo, resultado_posting, reporte, html_buffer,
            datos_fuente=datos_fuente_posting,
            label_fuente=label_fuente_posting,
        )
        if oficial:
            _mostrar_resumenes_palermo_posting(
                diffs,
                coincide_bases=resultados_pal["coincide"],
                diferencias_bases=resultados_pal["diferencias"],
                coincide_oficial=resultados_of["coincide"],
                diferencias_oficial=resultados_of["diferencias"],
                resultado_posting=resultado_posting,
                label_fuente=label_fuente_posting,
                vista_par=True,
            )
        else:
            _mostrar_resumenes_palermo_posting(
                diffs,
                coincide_bases=resultado["coincide"],
                diferencias_bases=resultado["diferencias"],
                titulo_bases="PALERMO vs REPORTE",
                resultado_posting=resultado_posting,
                label_fuente=label_fuente_posting,
                vista_par=True,
            )

    _exportar_html_si_corresponde(html_buffer, "palermo", diffs, meta, ruta_html=html, preguntar=html is None)


@app.command()
def la_plata(
    planilla: Path = typer.Argument(..., help="Ruta a la planilla XLS", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
    html: Optional[Path] = typer.Option(None, "--html", help="Exportar comparacion completa a HTML", dir_okay=False, resolve_path=True),
):
    """Compara Planilla XLS vs Reporte TXT para LA PLATA."""
    html_buffer: list[SeccionComparacionHtml] = []
    diffs: list[tuple[str, list[str]]] = []
    meta = [f"Planilla: {planilla.name}", f"Reporte: {reporte.name}"]

    with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
        resultado = _agente.comparar_laplata(planilla, reporte)
    datos_posting_lp = None
    resultado_posting = None
    if posting:
        meta.append(f"Posting: {', '.join(p.name for p in posting)}")
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting_lp = resultado_posting["datos_posting"]
    par_posting = _con_posting(posting, resultado_posting)
    bloque = imprimir_tabla_laplata(
        resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_lp,
        html_buffer=html_buffer,
        imprimir=not par_posting,
        compacto=par_posting,
        par=par_posting,
    )
    if par_posting:
        _imprimir_comparacion_con_posting(
            bloque, resultado_posting, reporte, html_buffer,
            datos_fuente=resultado["datos_planilla"],
            datos_reporte_meta=resultado["datos_reporte"],
            label_fuente="Planilla",
        )
        _mostrar_resumenes_posting(
            "Planilla", resultado, resultado_posting, diffs, vista_par=True,
        )
    else:
        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")
        diffs.append(("PLANILLA vs REPORTE", resultado["diferencias"]))

    _exportar_html_si_corresponde(html_buffer, "la_plata", diffs, meta, ruta_html=html, preguntar=html is None)


@app.command()
def auto(
    carpeta: Path = typer.Argument(..., help="Ruta a la carpeta con los archivos", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
):
    """Detecta automaticamente los archivos en una carpeta y ejecuta la comparacion."""
    with console.status("[bold blue]Escaneando archivos...[/bold blue]"):
        deteccion = detectar_archivos(carpeta)
    if "error" in deteccion:
        console.print(f"[red]{deteccion['error']}[/red]")
        raise typer.Exit(1)

    disponibles = hipodromos_detectados(deteccion)

    if not disponibles:
        console.print("[yellow]No se detectaron archivos suficientes para ningun hipodromo.[/yellow]")
        resumen = resumen_deteccion(deteccion)
        for hipodromo, archivos in resumen.items():
            console.print(f"  {hipodromo}: {', '.join(archivos)}")
        console.print("\n[yellow]Se necesita al menos 1 PDF + 1 TXT (reporte) o 1 XLS + 1 TXT.[/yellow]")
        raise typer.Exit(1)

    if len(disponibles) == 1:
        seleccion = disponibles[0]
    else:
        seleccion = menu_auto_detect(disponibles, resumen_deteccion(deteccion))
        if seleccion is None:
            console.print("[yellow]Operacion cancelada.[/yellow]")
            raise typer.Exit()

    ejecutar_auto_comparacion(seleccion, deteccion)


def ejecutar_auto_comparacion(seleccion: str, deteccion: dict) -> None:
    info = deteccion.get(seleccion, {})
    if seleccion == "san_isidro":
        pdf = info.get("pdf")
        reporte = info.get("reporte")
        posting = info.get("posting", [])
        if not pdf or not reporte:
            console.print("[red]Faltan archivos para San Isidro.[/red]")
            return
        html_buffer: list[SeccionComparacionHtml] = []
        diffs: list[tuple[str, list[str]]] = []
        meta = [f"PDF: {pdf.name}", f"Reporte: {reporte.name}"]

        with console.status("[bold blue]Comparando San Isidro...[/bold blue]"):
            resultado = _agente.comparar_san_isidro(pdf, reporte)
        meta.append(f"Tipo PDF: {resultado.get('tipo_pdf', 'OFICIAL')}")

        datos_posting_auto = None
        resultado_posting = None
        if posting:
            meta.append(f"Posting: {', '.join(p.name for p in posting)}")
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto = resultado_posting["datos_posting"]

        par_posting = _con_posting(posting, resultado_posting)
        bloque = imprimir_tabla_san_isidro(
            resultado["datos_pdf"], resultado["datos_reporte"], datos_posting_auto,
            resultado.get("fecha_reporte"), resultado.get("tipo_pdf"), html_buffer=html_buffer,
            imprimir=not par_posting,
            compacto=par_posting,
            par=par_posting,
        )
        if par_posting:
            _imprimir_comparacion_con_posting(
                bloque, resultado_posting, reporte, html_buffer,
                datos_fuente=resultado["datos_pdf"],
                datos_reporte_meta=resultado["datos_reporte"],
                label_fuente=resultado.get("tipo_pdf", "OFICIAL"),
            )
            _mostrar_resumenes_posting(
                resultado.get("tipo_pdf", "OFICIAL"), resultado, resultado_posting, diffs,
                vista_par=True,
            )
        else:
            label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
            diffs.append((label, resultado["diferencias"]))

        _exportar_html_si_corresponde(html_buffer, "san_isidro", diffs, meta)

    elif seleccion == "palermo":
        bases = info.get("bases_pdf")
        reporte = info.get("reporte")
        oficial_pdf = info.get("oficial_pdf")
        posting = info.get("posting", [])
        if not bases or not reporte:
            console.print("[red]Faltan archivos para Palermo.[/red]")
            return
        html_buffer = []
        diffs: list[tuple[str, list[str]]] = []
        meta = [f"Bases: {bases.name}", f"Reporte: {reporte.name}"]
        if oficial_pdf:
            meta.append(f"Oficial: {oficial_pdf.name}")

        datos_posting_auto = None
        resultado_posting = None
        if posting:
            meta.append(f"Posting: {', '.join(p.name for p in posting)}")
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto = resultado_posting["datos_posting"]
        datos_fuente_posting: Optional[dict] = None
        label_fuente_posting = "Bases Palermo"
        par_posting = _con_posting(posting, resultado_posting)
        bloque_palermo: Optional[BloqueComparacion] = None
        if oficial_pdf:
            with console.status("[bold blue]Comparando Palermo (completo)...[/bold blue]"):
                resultado = _agente.comparar_palermo_con_oficial(bases, reporte, oficial_pdf)
            resultados_pal = resultado["palermo_vs_reporte"]
            datos_fuente_posting = resultados_pal["datos_pdf"]
            bloque_palermo = imprimir_tablas_palermo(
                resultados_pal["datos_pdf"],
                resultados_pal["datos_reporte"],
                resultados_pal.get("fechas_detectadas", []),
                resultados_pal.get("fecha_usada"),
                datos_posting=datos_posting_auto,
                html_buffer=html_buffer,
                imprimir=not par_posting,
        compacto=par_posting,
        par=par_posting,
            )
            if not par_posting:
                mostrar_resumen_comparacion(resultados_pal["coincide"], resultados_pal["diferencias"], "PALERMO BASES vs REPORTE")
                diffs.append(("PALERMO BASES vs REPORTE", resultados_pal["diferencias"]))
                mostrar_resumen_comparacion(resultado["oficial_vs_reporte"]["coincide"], resultado["oficial_vs_reporte"]["diferencias"], "OFICIAL vs REPORTE")
                diffs.append(("OFICIAL vs REPORTE", resultado["oficial_vs_reporte"]["diferencias"]))
        else:
            with console.status("[bold blue]Comparando Palermo (bases)...[/bold blue]"):
                resultado = _agente.comparar_palermo(bases, reporte)
            datos_fuente_posting = resultado["datos_pdf"]
            bloque_palermo = imprimir_tablas_palermo(
                resultado["datos_pdf"],
                resultado["datos_reporte"],
                resultado.get("fechas_detectadas", []),
                resultado.get("fecha_usada"),
                datos_posting=datos_posting_auto,
                html_buffer=html_buffer,
                imprimir=not par_posting,
        compacto=par_posting,
        par=par_posting,
            )
            if not par_posting:
                mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")
                diffs.append(("PALERMO vs REPORTE", resultado["diferencias"]))
        if par_posting and bloque_palermo is not None:
            _imprimir_comparacion_con_posting(
                bloque_palermo, resultado_posting, reporte, html_buffer,
                datos_fuente=datos_fuente_posting,
                label_fuente=label_fuente_posting,
            )
            if oficial_pdf:
                _mostrar_resumenes_palermo_posting(
                    diffs,
                    coincide_bases=resultados_pal["coincide"],
                    diferencias_bases=resultados_pal["diferencias"],
                    coincide_oficial=resultado["oficial_vs_reporte"]["coincide"],
                    diferencias_oficial=resultado["oficial_vs_reporte"]["diferencias"],
                    resultado_posting=resultado_posting,
                    label_fuente=label_fuente_posting,
                    vista_par=True,
                )
            else:
                _mostrar_resumenes_palermo_posting(
                    diffs,
                    coincide_bases=resultado["coincide"],
                    diferencias_bases=resultado["diferencias"],
                    titulo_bases="PALERMO vs REPORTE",
                    resultado_posting=resultado_posting,
                    label_fuente=label_fuente_posting,
                    vista_par=True,
                )
        _exportar_html_si_corresponde(html_buffer, "palermo", diffs, meta)

    elif seleccion == "la_plata":
        planilla = info.get("planilla")
        reporte = info.get("reporte")
        posting = info.get("posting", [])
        if not planilla or not reporte:
            console.print("[red]Faltan archivos para La Plata.[/red]")
            return
        html_buffer = []
        diffs = []
        meta = [f"Planilla: {planilla.name}", f"Reporte: {reporte.name}"]

        with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
            resultado = _agente.comparar_laplata(planilla, reporte)
        datos_posting_auto_lp = None
        resultado_posting = None
        if posting:
            meta.append(f"Posting: {', '.join(p.name for p in posting)}")
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto_lp = resultado_posting["datos_posting"]
        par_posting = _con_posting(posting, resultado_posting)
        bloque = imprimir_tabla_laplata(
            resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_auto_lp,
            html_buffer=html_buffer,
            imprimir=not par_posting,
            compacto=par_posting,
            par=par_posting,
        )
        if par_posting:
            _imprimir_comparacion_con_posting(
                bloque, resultado_posting, reporte, html_buffer,
                datos_fuente=resultado["datos_planilla"],
                datos_reporte_meta=resultado["datos_reporte"],
                label_fuente="Planilla",
            )
            _mostrar_resumenes_posting(
                "Planilla", resultado, resultado_posting, diffs, vista_par=True,
            )
        else:
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")
            diffs.append(("PLANILLA vs REPORTE", resultado["diferencias"]))
        _exportar_html_si_corresponde(html_buffer, "la_plata", diffs, meta)


@app.command()
def menu():
    """Modo interactivo con menus (experiencia clasica mejorada)."""
    while True:
        opcion = menu_principal()
        if opcion == 1:
            _menu_san_isidro_interactivo()
        elif opcion == 2:
            _menu_palermo_interactivo()
        elif opcion == 3:
            _menu_laplata_interactivo()
        elif opcion == 4:
            ruta = seleccionar_carpeta()
            if not ruta:
                console.print("[yellow]No se selecciono ninguna carpeta.[/yellow]")
                Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
                continue
            ruta_p = Path(ruta).resolve()
            with console.status("[bold blue]Escaneando archivos...[/bold blue]"):
                deteccion = detectar_archivos(ruta_p)
            disponibles = hipodromos_detectados(deteccion)
            if not disponibles:
                console.print("[yellow]No se detectaron archivos suficientes.[/yellow]")
                Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
                continue
            if len(disponibles) == 1:
                seleccion = disponibles[0]
            else:
                seleccion = menu_auto_detect(disponibles, resumen_deteccion(deteccion))
                if seleccion is None:
                    continue
            ejecutar_auto_comparacion(seleccion, deteccion)
            Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        elif opcion == 5:
            _menu_control_xml_interactivo()
        elif opcion == 6:
            console.print("[bold]Saliendo del programa.[/bold]")
            raise typer.Exit()
        else:
            console.print("[red]Opcion no valida.[/red]")


# --- Modo interactivo ---

def _menu_control_xml_interactivo() -> None:
    limpiar_pantalla()
    console.rule("[bold]CONTROL XML[/bold]")
    ruta = seleccionar_archivo(
        "Ruta del archivo XML: ",
        {".xml"},
        "archivo XML",
    )
    if not ruta:
        console.print("[yellow]No se selecciono ningun archivo XML.[/yellow]")
        Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        return
    try:
        with console.status("[bold blue]Leyendo XML...[/bold blue]"):
            resultado = controlar_xml(ruta)
        imprimir_control_xml(resultado)
    except (ValueError, FileNotFoundError, OSError) as exc:
        console.print(f"[red]{exc}[/red]")
    Prompt.ask("[dim]Enter para continuar...[/dim]", default="")


@app.command("control-xml")
def control_xml_cmd(
    archivo: Path = typer.Argument(..., help="Ruta al archivo XML (ARG_HSI_* o ARG_LP_*)"),
):
    """Resumen de carreras y caballos desde XML de San Isidro o La Plata."""
    try:
        resultado = controlar_xml(archivo)
    except (ValueError, FileNotFoundError, OSError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    imprimir_control_xml(resultado)


def _menu_san_isidro_interactivo():
    ruta_pdf = None
    ruta_reporte = None
    rutas_posting: list[Path] = []

    while True:
        archivos = {
            "PDF seleccionado": ruta_pdf,
            "Reporte seleccionado": ruta_reporte,
            "Posting Prices": f"{len(rutas_posting)} archivo(s)" if rutas_posting else None,
        }
        op = mostrar_menu_archivos(
            "COMPARAR ARCHIVOS - SAN ISIDRO",
            archivos,
            [
                ("1", "Seleccionar programa oficial o tela (PDF)"),
                ("2", "Seleccionar reporte (TXT)"),
                ("3", "Seleccionar Posting Prices (TXT)"),
                ("4", "COMPARAR ARCHIVOS"),
                ("5", "Resumen de tela oficial (PDF)"),
                ("6", "Volver al menu principal"),
            ],
        )

        if op == "1":
            ruta = seleccionar_archivo("Ruta del PDF: ", {".pdf"}, "programa oficial o tela (PDF)")
            if ruta:
                ruta_pdf = ruta
        elif op == "2":
            ruta = seleccionar_archivo("Ruta del reporte TXT: ", {".txt"}, "reporte (TXT)")
            if ruta:
                ruta_reporte = ruta
        elif op == "3":
            rutas_posting = []
            for i in range(1, 3):
                ruta = seleccionar_archivo(
                    f"Ruta del Posting #{i} TXT: ", {".txt"}, f"Posting Prices #{i} (TXT)"
                )
                if not ruta:
                    if i == 1:
                        console.print("[yellow]No se selecciono archivo de Posting.[/yellow]")
                    break
                rutas_posting.append(Path(ruta))
        elif op == "4":
            if not ruta_pdf or not ruta_reporte:
                console.print("[red]Debe seleccionar PDF y Reporte primero.[/red]")
                Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
                continue
            html_buffer: list[SeccionComparacionHtml] = []
            diffs: list[tuple[str, list[str]]] = []
            meta = [f"PDF: {Path(ruta_pdf).name}", f"Reporte: {Path(ruta_reporte).name}"]

            with console.status("[bold blue]Comparando...[/bold blue]"):
                resultado = _agente.comparar_san_isidro(ruta_pdf, ruta_reporte)
            meta.append(f"Tipo PDF: {resultado.get('tipo_pdf', 'OFICIAL')}")

            datos_posting_menu = None
            res_p = None
            if rutas_posting:
                meta.append(f"Posting: {', '.join(p.name for p in rutas_posting)}")
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu = res_p["datos_posting"]
            par_posting = bool(rutas_posting and res_p)
            bloque = imprimir_tabla_san_isidro(
                resultado["datos_pdf"], resultado["datos_reporte"], datos_posting_menu,
                resultado.get("fecha_reporte"), resultado.get("tipo_pdf"), html_buffer=html_buffer,
                imprimir=not par_posting,
                compacto=par_posting,
                par=par_posting,
            )
            if par_posting:
                _imprimir_comparacion_con_posting(
                    bloque, res_p, ruta_reporte, html_buffer,
                    datos_fuente=resultado["datos_pdf"],
                    datos_reporte_meta=resultado["datos_reporte"],
                    label_fuente=resultado.get("tipo_pdf", "OFICIAL"),
                )
                _mostrar_resumenes_posting(
                    resultado.get("tipo_pdf", "OFICIAL"), resultado, res_p, diffs,
                    vista_par=True,
                )
            else:
                label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
                mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
                diffs.append((label, resultado["diferencias"]))
            _exportar_html_si_corresponde(html_buffer, "san_isidro", diffs, meta)
            Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        elif op == "5":
            _resumen_tela_interactivo()
        elif op == "6":
            return


def _resumen_tela_interactivo():
    ruta = seleccionar_archivo("Ruta de la tela oficial (PDF): ", {".pdf"}, "tela oficial (PDF)")
    if not ruta:
        return
    if not es_tela_oficial(ruta):
        console.print("[red]El archivo seleccionado no es una tela oficial (no contiene 'Programa Depurado').[/red]")
        Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        return
    with console.status("[bold blue]Analizando tela oficial...[/bold blue]"):
        apuestas_raw = obtener_apuestas_por_carrera(ruta)
        datos = normalizar_desde_lista_apuestas(apuestas_raw)
        pases = extraer_pases_tela_oficial(ruta)
        for num_carrera, pases_carrera in pases.items():
            if num_carrera in datos:
                datos[num_carrera]["pases"] = pases_carrera
    limpiar_pantalla()
    console.rule("[bold]RESUMEN TELA OFICIAL[/bold]")
    console.print()
    imprimir_resumen_tela(datos, ruta)
    if Confirm.ask("¿Guardar como HTML para imprimir?", default=False):
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        desktop = Path(_os.path.expanduser("~/Desktop"))
        salida = desktop / f"ControlComparador_{ts}.html"
        with console.status("[bold green]Generando HTML...[/bold green]"):
            exportar_resumen_html(datos, ruta, salida)
        console.print(f"[green]HTML guardado en:[/green] {salida}")
        _os.startfile(salida)
    Prompt.ask("[dim]Enter para continuar...[/dim]", default="")


def _menu_palermo_interactivo():
    ruta_bases = None
    ruta_reporte = None
    ruta_oficial = None
    rutas_posting: list[Path] = []

    while True:
        archivos = {
            "Bases y Apuestas Palermo (PDF)": ruta_bases,
            "Reporte seleccionado": ruta_reporte,
            "Oficial seleccionado (PDF)": ruta_oficial,
            "Posting Prices": f"{len(rutas_posting)} archivo(s)" if rutas_posting else None,
        }
        op = mostrar_menu_archivos(
            "COMPARAR ARCHIVOS - PALERMO",
            archivos,
            [
                ("1", "Seleccionar Bases y Apuestas Palermo (PDF)"),
                ("2", "Seleccionar reporte (TXT)"),
                ("3", "Seleccionar oficial (PDF)"),
                ("4", "Seleccionar Posting Prices (TXT)"),
                ("5", "COMPARAR ARCHIVOS"),
                ("6", "Volver al menu principal"),
            ],
        )

        if op == "1":
            ruta = seleccionar_archivo("Ruta del PDF Palermo: ", {".pdf"}, "Bases y Apuestas Palermo (PDF)")
            if ruta:
                ruta_bases = ruta
        elif op == "2":
            ruta = seleccionar_archivo("Ruta del reporte TXT: ", {".txt"}, "reporte (TXT)")
            if ruta:
                ruta_reporte = ruta
        elif op == "3":
            ruta = seleccionar_archivo("Ruta del PDF oficial: ", {".pdf"}, "oficial (PDF)")
            if ruta:
                ruta_oficial = ruta
        elif op == "4":
            rutas_posting = []
            for i in range(1, 3):
                ruta = seleccionar_archivo(
                    f"Ruta del Posting #{i} TXT: ", {".txt"}, f"Posting Prices #{i} (TXT)"
                )
                if not ruta:
                    break
                rutas_posting.append(Path(ruta))
        elif op == "5":
            if not ruta_bases or not ruta_reporte:
                console.print("[red]Debe seleccionar Bases PDF y Reporte TXT primero.[/red]")
                Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
                continue
            html_buffer: list[SeccionComparacionHtml] = []
            diffs: list[tuple[str, list[str]]] = []
            meta = [f"Bases: {Path(ruta_bases).name}", f"Reporte: {Path(ruta_reporte).name}"]
            if ruta_oficial:
                meta.append(f"Oficial: {Path(ruta_oficial).name}")

            datos_posting_menu = None
            res_p = None
            datos_fuente_posting: Optional[dict] = None
            label_fuente_posting = "Bases Palermo"
            par_posting = False
            bloque_palermo: Optional[BloqueComparacion] = None
            if rutas_posting:
                meta.append(f"Posting: {', '.join(p.name for p in rutas_posting)}")
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu = res_p["datos_posting"]
                    par_posting = True
            with console.status("[bold blue]Comparando Palermo...[/bold blue]"):
                if ruta_oficial:
                    resultado = _agente.comparar_palermo_con_oficial(ruta_bases, ruta_reporte, ruta_oficial)
                    resultados_pal = resultado["palermo_vs_reporte"]
                    datos_fuente_posting = resultados_pal["datos_pdf"]
                    bloque_palermo = imprimir_tablas_palermo(
                        resultados_pal["datos_pdf"],
                        resultados_pal["datos_reporte"],
                        resultados_pal.get("fechas_detectadas", []),
                        resultados_pal.get("fecha_usada"),
                        datos_posting=datos_posting_menu,
                        html_buffer=html_buffer,
                        imprimir=not par_posting,
                        compacto=par_posting,
                        par=par_posting,
                    )
                    if not par_posting:
                        mostrar_resumen_comparacion(
                            resultados_pal["coincide"],
                            resultados_pal["diferencias"],
                            "PALERMO BASES vs REPORTE",
                        )
                        diffs.append(("PALERMO BASES vs REPORTE", resultados_pal["diferencias"]))
                        mostrar_resumen_comparacion(
                            resultado["oficial_vs_reporte"]["coincide"],
                            resultado["oficial_vs_reporte"]["diferencias"],
                            "OFICIAL vs REPORTE",
                        )
                        diffs.append(("OFICIAL vs REPORTE", resultado["oficial_vs_reporte"]["diferencias"]))
                else:
                    resultado = _agente.comparar_palermo(ruta_bases, ruta_reporte)
                    datos_fuente_posting = resultado["datos_pdf"]
                    bloque_palermo = imprimir_tablas_palermo(
                        resultado["datos_pdf"],
                        resultado["datos_reporte"],
                        resultado.get("fechas_detectadas", []),
                        resultado.get("fecha_usada"),
                        datos_posting=datos_posting_menu,
                        html_buffer=html_buffer,
                        imprimir=not par_posting,
                        compacto=par_posting,
                        par=par_posting,
                    )
                    if not par_posting:
                        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")
                        diffs.append(("PALERMO vs REPORTE", resultado["diferencias"]))

            if par_posting and bloque_palermo is not None:
                _imprimir_comparacion_con_posting(
                    bloque_palermo, res_p, ruta_reporte, html_buffer,
                    datos_fuente=datos_fuente_posting,
                    label_fuente=label_fuente_posting,
                )
                if ruta_oficial:
                    _mostrar_resumenes_palermo_posting(
                        diffs,
                        coincide_bases=resultados_pal["coincide"],
                        diferencias_bases=resultados_pal["diferencias"],
                        coincide_oficial=resultado["oficial_vs_reporte"]["coincide"],
                        diferencias_oficial=resultado["oficial_vs_reporte"]["diferencias"],
                        resultado_posting=res_p,
                        label_fuente=label_fuente_posting,
                        vista_par=True,
                    )
                else:
                    _mostrar_resumenes_palermo_posting(
                        diffs,
                        coincide_bases=resultado["coincide"],
                        diferencias_bases=resultado["diferencias"],
                        titulo_bases="PALERMO vs REPORTE",
                        resultado_posting=res_p,
                        label_fuente=label_fuente_posting,
                        vista_par=True,
                    )
            _exportar_html_si_corresponde(html_buffer, "palermo", diffs, meta)
            Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        elif op == "6":
            return


def _menu_laplata_interactivo():
    ruta_planilla = None
    ruta_reporte = None
    rutas_posting: list[Path] = []

    while True:
        archivos = {
            "Planilla La Plata (XLS)": ruta_planilla,
            "Reporte seleccionado": ruta_reporte,
            "Posting Prices": f"{len(rutas_posting)} archivo(s)" if rutas_posting else None,
        }
        op = mostrar_menu_archivos(
            "COMPARAR ARCHIVOS - LA PLATA",
            archivos,
            [
                ("1", "Seleccionar planilla (XLS)"),
                ("2", "Seleccionar reporte (TXT)"),
                ("3", "Seleccionar Posting Prices (TXT)"),
                ("4", "COMPARAR ARCHIVOS"),
                ("5", "Volver al menu principal"),
            ],
        )

        if op == "1":
            ruta = seleccionar_archivo("Ruta de la planilla XLS: ", {".xls"}, "planilla La Plata (XLS)")
            if ruta:
                ruta_planilla = ruta
        elif op == "2":
            ruta = seleccionar_archivo("Ruta del reporte TXT: ", {".txt"}, "reporte (TXT)")
            if ruta:
                ruta_reporte = ruta
        elif op == "3":
            rutas_posting = []
            for i in range(1, 3):
                ruta = seleccionar_archivo(
                    f"Ruta del Posting #{i} TXT: ", {".txt"}, f"Posting Prices #{i} (TXT)"
                )
                if not ruta:
                    break
                rutas_posting.append(Path(ruta))
        elif op == "4":
            if not ruta_planilla or not ruta_reporte:
                console.print("[red]Debe seleccionar Planilla XLS y Reporte TXT primero.[/red]")
                Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
                continue
            html_buffer: list[SeccionComparacionHtml] = []
            diffs: list[tuple[str, list[str]]] = []
            meta = [f"Planilla: {Path(ruta_planilla).name}", f"Reporte: {Path(ruta_reporte).name}"]

            with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
                resultado = _agente.comparar_laplata(ruta_planilla, ruta_reporte)
            datos_posting_menu_lp = None
            res_p = None
            par_posting = False
            if rutas_posting:
                meta.append(f"Posting: {', '.join(p.name for p in rutas_posting)}")
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu_lp = res_p["datos_posting"]
                    par_posting = True
            bloque = imprimir_tabla_laplata(
                resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_menu_lp,
                html_buffer=html_buffer,
                imprimir=not par_posting,
        compacto=par_posting,
        par=par_posting,
            )
            if par_posting:
                _imprimir_comparacion_con_posting(
                    bloque, res_p, ruta_reporte, html_buffer,
                    datos_fuente=resultado["datos_planilla"],
                    datos_reporte_meta=resultado["datos_reporte"],
                    label_fuente="Planilla",
                )
                _mostrar_resumenes_posting(
                    "Planilla", resultado, res_p, diffs, vista_par=True,
                )
            else:
                mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")
                diffs.append(("PLANILLA vs REPORTE", resultado["diferencias"]))
            _exportar_html_si_corresponde(html_buffer, "la_plata", diffs, meta)
            Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        elif op == "5":
            return


def main():
    import sys
    if len(sys.argv) == 1:
        menu()
    else:
        app()
