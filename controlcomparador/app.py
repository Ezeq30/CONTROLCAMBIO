# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import typer
import os as _os
from datetime import datetime
from pathlib import Path
from rich.prompt import Prompt, Confirm

from controlcomparador import __version__
from controlcomparador.agent import AgenteComparacion
from controlcomparador.detector import detectar_archivos, hipodromos_detectados, resumen_deteccion
from controlcomparador.parsers.pdf import es_tela_oficial, obtener_apuestas_por_carrera, normalizar_desde_lista_apuestas, extraer_pases_tela_oficial
from controlcomparador.ui.console import console
from controlcomparador.ui.tables import (
    exportar_resumen_html,
    imprimir_tabla_san_isidro,
    imprimir_tablas_palermo,
    imprimir_tabla_laplata,
    imprimir_tabla_posting_vs_reporte,
    imprimir_resumen_tela,
    mostrar_resumen_comparacion,
)
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


@app.command()
def version():
    """Muestra la version del programa."""
    console.print(f"[bold]ControlComparador[/bold] v{__version__}")


@app.command()
def san_isidro(
    pdf: Path = typer.Argument(..., help="Ruta al PDF del programa oficial", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
):
    """Compara PDF vs Reporte para SAN ISIDRO."""
    with console.status("[bold blue]Comparando San Isidro...[/bold blue]"):
        resultado = _agente.comparar_san_isidro(pdf, reporte)
    datos_posting = None
    if posting:
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting = resultado_posting["datos_posting"]
    imprimir_tabla_san_isidro(resultado["datos_pdf"], resultado["datos_reporte"], datos_posting, resultado.get("fecha_reporte"), resultado.get("tipo_pdf"))
    label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
    mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
    if posting:
        mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")


@app.command()
def palermo(
    bases: Path = typer.Argument(..., help="Ruta al PDF de Bases y Apuestas Palermo", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    oficial: Optional[Path] = typer.Option(None, "--oficial", "-o", help="Ruta al PDF oficial Palermo", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
    fecha: Optional[str] = typer.Option(None, "--fecha", "-f", help="Fecha objetivo (dd/mm/aaaa)"),
):
    """Compara PDF vs Reporte para PALERMO."""
    datos_posting = None
    if posting:
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting = resultado_posting["datos_posting"]

    if oficial:
        with console.status("[bold blue]Comparando Palermo (completo)...[/bold blue]"):
            resultado = _agente.comparar_palermo_con_oficial(bases, reporte, oficial, fecha_objetivo=fecha)
        resultados_pal = resultado["palermo_vs_reporte"]
        resultados_of = resultado["oficial_vs_reporte"]
        imprimir_tablas_palermo(
            resultados_pal["datos_pdf"],
            resultados_pal["datos_reporte"],
            resultados_pal.get("fechas_detectadas", []),
            resultados_pal.get("fecha_usada"),
            datos_posting=datos_posting,
        )
        mostrar_resumen_comparacion(resultados_pal["coincide"], resultados_pal["diferencias"], "PALERMO BASES vs REPORTE")
        mostrar_resumen_comparacion(resultados_of["coincide"], resultados_of["diferencias"], "OFICIAL vs REPORTE")
    else:
        with console.status("[bold blue]Comparando Palermo (bases)...[/bold blue]"):
            resultado = _agente.comparar_palermo(bases, reporte, fecha_objetivo=fecha)
        imprimir_tablas_palermo(
            resultado["datos_pdf"],
            resultado["datos_reporte"],
            resultado.get("fechas_detectadas", []),
            resultado.get("fecha_usada"),
            datos_posting=datos_posting,
        )
        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")

    if posting:
        mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")


@app.command()
def la_plata(
    planilla: Path = typer.Argument(..., help="Ruta a la planilla XLS", exists=True, dir_okay=False, resolve_path=True),
    reporte: Path = typer.Argument(..., help="Ruta al archivo de reporte TXT", exists=True, dir_okay=False, resolve_path=True),
    posting: Optional[List[Path]] = typer.Option(None, "--posting", "-p", help="Archivo(s) de Posting Prices (hasta 2)", exists=True, dir_okay=False, resolve_path=True),
):
    """Compara Planilla XLS vs Reporte TXT para LA PLATA."""
    with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
        resultado = _agente.comparar_laplata(planilla, reporte)
    datos_posting_lp = None
    if posting:
        with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
            resultado_posting = _agente.comparar_posting(posting, reporte)
            datos_posting_lp = resultado_posting["datos_posting"]
    imprimir_tabla_laplata(resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_lp)
    mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")

    if posting:
        mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")


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
        with console.status("[bold blue]Comparando San Isidro...[/bold blue]"):
            resultado = _agente.comparar_san_isidro(pdf, reporte)
        datos_posting_auto = None
        if posting:
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto = resultado_posting["datos_posting"]
        imprimir_tabla_san_isidro(resultado["datos_pdf"], resultado["datos_reporte"], datos_posting_auto, resultado.get("fecha_reporte"), resultado.get("tipo_pdf"))
        label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
        if posting:
            mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")

    elif seleccion == "palermo":
        bases = info.get("bases_pdf")
        reporte = info.get("reporte")
        oficial_pdf = info.get("oficial_pdf")
        posting = info.get("posting", [])
        if not bases or not reporte:
            console.print("[red]Faltan archivos para Palermo.[/red]")
            return
        datos_posting_auto = None
        if posting:
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto = resultado_posting["datos_posting"]
        if oficial_pdf:
            with console.status("[bold blue]Comparando Palermo (completo)...[/bold blue]"):
                resultado = _agente.comparar_palermo_con_oficial(bases, reporte, oficial_pdf)
            resultados_pal = resultado["palermo_vs_reporte"]
            imprimir_tablas_palermo(
                resultados_pal["datos_pdf"],
                resultados_pal["datos_reporte"],
                resultados_pal.get("fechas_detectadas", []),
                resultados_pal.get("fecha_usada"),
                datos_posting=datos_posting_auto,
            )
            mostrar_resumen_comparacion(resultados_pal["coincide"], resultados_pal["diferencias"], "PALERMO BASES vs REPORTE")
            mostrar_resumen_comparacion(resultado["oficial_vs_reporte"]["coincide"], resultado["oficial_vs_reporte"]["diferencias"], "OFICIAL vs REPORTE")
        else:
            with console.status("[bold blue]Comparando Palermo (bases)...[/bold blue]"):
                resultado = _agente.comparar_palermo(bases, reporte)
            imprimir_tablas_palermo(
                resultado["datos_pdf"],
                resultado["datos_reporte"],
                resultado.get("fechas_detectadas", []),
                resultado.get("fecha_usada"),
                datos_posting=datos_posting_auto,
            )
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")
        if posting:
            mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")

    elif seleccion == "la_plata":
        planilla = info.get("planilla")
        reporte = info.get("reporte")
        posting = info.get("posting", [])
        if not planilla or not reporte:
            console.print("[red]Faltan archivos para La Plata.[/red]")
            return
        with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
            resultado = _agente.comparar_laplata(planilla, reporte)
        datos_posting_auto_lp = None
        if posting:
            with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                resultado_posting = _agente.comparar_posting(posting, reporte)
                datos_posting_auto_lp = resultado_posting["datos_posting"]
        imprimir_tabla_laplata(resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_auto_lp)
        mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")
        if posting:
            mostrar_resumen_comparacion(resultado_posting["coincide"], resultado_posting["diferencias"], "POSTING vs REPORTE")


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
            console.print("[bold]Saliendo del programa.[/bold]")
            raise typer.Exit()
        else:
            console.print("[red]Opcion no valida.[/red]")


# --- Modo interactivo ---

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
            with console.status("[bold blue]Comparando...[/bold blue]"):
                resultado = _agente.comparar_san_isidro(ruta_pdf, ruta_reporte)
            datos_posting_menu = None
            if rutas_posting:
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu = res_p["datos_posting"]
            imprimir_tabla_san_isidro(resultado["datos_pdf"], resultado["datos_reporte"], datos_posting_menu, resultado.get("fecha_reporte"), resultado.get("tipo_pdf"))
            label = f"{resultado.get('tipo_pdf', 'OFICIAL')} vs REPORTE"
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], label)
            if rutas_posting:
                mostrar_resumen_comparacion(res_p["coincide"], res_p["diferencias"], "POSTING vs REPORTE")
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
            datos_posting_menu = None
            if rutas_posting:
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu = res_p["datos_posting"]
            with console.status("[bold blue]Comparando Palermo...[/bold blue]"):
                if ruta_oficial:
                    resultado = _agente.comparar_palermo_con_oficial(ruta_bases, ruta_reporte, ruta_oficial)
                    resultados_pal = resultado["palermo_vs_reporte"]
                    imprimir_tablas_palermo(
                        resultados_pal["datos_pdf"],
                        resultados_pal["datos_reporte"],
                        resultados_pal.get("fechas_detectadas", []),
                        resultados_pal.get("fecha_usada"),
                        datos_posting=datos_posting_menu,
                    )
                    mostrar_resumen_comparacion(
                        resultados_pal["coincide"],
                        resultados_pal["diferencias"],
                        "PALERMO BASES vs REPORTE",
                    )
                    mostrar_resumen_comparacion(
                        resultado["oficial_vs_reporte"]["coincide"],
                        resultado["oficial_vs_reporte"]["diferencias"],
                        "OFICIAL vs REPORTE",
                    )
                else:
                    resultado = _agente.comparar_palermo(ruta_bases, ruta_reporte)
                    imprimir_tablas_palermo(
                        resultado["datos_pdf"],
                        resultado["datos_reporte"],
                        resultado.get("fechas_detectadas", []),
                        resultado.get("fecha_usada"),
                        datos_posting=datos_posting_menu,
                    )
                    mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PALERMO vs REPORTE")

            if rutas_posting:
                mostrar_resumen_comparacion(res_p["coincide"], res_p["diferencias"], "POSTING vs REPORTE")
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
            with console.status("[bold blue]Comparando La Plata...[/bold blue]"):
                resultado = _agente.comparar_laplata(ruta_planilla, ruta_reporte)
            datos_posting_menu_lp = None
            if rutas_posting:
                with console.status("[bold blue]Comparando Posting Prices...[/bold blue]"):
                    res_p = _agente.comparar_posting(rutas_posting, ruta_reporte)
                    datos_posting_menu_lp = res_p["datos_posting"]
            imprimir_tabla_laplata(resultado["datos_planilla"], resultado["datos_reporte"], datos_posting_menu_lp)
            mostrar_resumen_comparacion(resultado["coincide"], resultado["diferencias"], "PLANILLA vs REPORTE")

            if rutas_posting:
                mostrar_resumen_comparacion(res_p["coincide"], res_p["diferencias"], "POSTING vs REPORTE")
            Prompt.ask("[dim]Enter para continuar...[/dim]", default="")
        elif op == "5":
            return


def main():
    import sys
    if len(sys.argv) == 1:
        menu()
    else:
        app()
