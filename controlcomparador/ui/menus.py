# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich import box

from controlcomparador.ui.console import console
from controlcomparador.ui.tables import (
    imprimir_tabla_san_isidro,
    imprimir_tablas_palermo,
    imprimir_tabla_laplata,
    imprimir_tabla_posting_vs_reporte,
    mostrar_resumen_comparacion,
)


def limpiar_pantalla() -> None:
    import os
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def seleccionar_archivo_ruta(mensaje: str, extensiones: set[str]) -> Optional[str]:
    while True:
        ruta = input(mensaje).strip().strip('"')
        if not ruta:
            return None
        p = Path(ruta)
        if not p.is_file():
            console.print("[red]La ruta ingresada no es un archivo valido. Intente nuevamente.[/red]")
            continue
        if extensiones and p.suffix.lower() not in extensiones:
            console.print(f"[red]Extension invalida. Se espera: {', '.join(sorted(extensiones))}[/red]")
            continue
        return ruta


def seleccionar_archivo_gui(extensiones: set[str], descripcion: str) -> Optional[str]:
    try:
        import tkinter as _tk
        from tkinter import filedialog as _filedialog
    except Exception:
        return None
    raiz = _tk.Tk()
    raiz.withdraw()
    patrones = []
    for ext in sorted(extensiones):
        patrones.append((f"Archivos {ext.upper()}", f"*{ext}"))
    patrones.append(("Todos los archivos", "*.*"))
    ruta = _filedialog.askopenfilename(
        title=f"Seleccionar {descripcion}",
        filetypes=patrones,
    )
    raiz.destroy()
    if not ruta:
        return None
    p = Path(ruta)
    if not p.is_file():
        return None
    if extensiones and p.suffix.lower() not in extensiones:
        return None
    return ruta


def seleccionar_archivo(mensaje: str, extensiones: set[str], descripcion: str) -> Optional[str]:
    ruta = seleccionar_archivo_gui(extensiones, descripcion)
    if not ruta:
        console.print("[yellow]No se selecciono archivo desde la ventana. Ingrese la ruta manualmente.[/yellow]")
        ruta = seleccionar_archivo_ruta(mensaje, extensiones)
    return ruta


def seleccionar_carpeta_ruta(mensaje: str) -> Optional[str]:
    while True:
        ruta = input(mensaje).strip().strip('"')
        if not ruta:
            return None
        p = Path(ruta)
        if not p.is_dir():
            console.print("[red]La ruta ingresada no es una carpeta valida. Intente nuevamente.[/red]")
            continue
        return ruta


def seleccionar_carpeta_gui() -> Optional[str]:
    try:
        import tkinter as _tk
        from tkinter import filedialog as _filedialog
    except Exception:
        return None
    raiz = _tk.Tk()
    raiz.withdraw()
    ruta = _filedialog.askdirectory(title="Seleccionar carpeta con archivos")
    raiz.destroy()
    if not ruta:
        return None
    p = Path(ruta)
    if not p.is_dir():
        return None
    return ruta


def seleccionar_carpeta() -> Optional[str]:
    ruta = seleccionar_carpeta_gui()
    if not ruta:
        console.print("[yellow]No se selecciono carpeta desde la ventana. Ingrese la ruta manualmente.[/yellow]")
        ruta = seleccionar_carpeta_ruta("Ruta de la carpeta: ")
    return ruta


def mostrar_menu_archivos(
    titulo: str,
    archivos: dict[str, Optional[str]],
    opciones: list[tuple[str, str]],
) -> str:
    limpiar_pantalla()
    table = Table(title=titulo, box=box.HEAVY, header_style="bold cyan")
    table.add_column("Op.", style="bold yellow", width=6)
    table.add_column("Accion")
    for num, desc in opciones:
        table.add_row(num, desc)
    console.print(table)

    for nombre, ruta in archivos.items():
        if ruta:
            console.print(f"  {nombre}: [green]{ruta}[/green]")
        else:
            console.print(f"  {nombre}: [dim](ninguno)[/dim]")

    opcion = Prompt.ask("\n[bold]Elija una opcion[/bold]", default="")
    return opcion.strip()


def menu_auto_detect(
    disponibles: list[str],
    resumen: dict[str, list[str]],
) -> Optional[str]:
    limpiar_pantalla()
    console.rule("[bold]SELECCIONAR COMPARACION[/bold]")
    console.print("[info]Se detectaron archivos de multiples hipodromos:[/info]\n")
    for hipodromo, archivos in resumen.items():
        if hipodromo.replace(" ", "_").lower() in disponibles:
            console.print(f"[bold]{hipodromo}[/bold]")
            for a in archivos:
                console.print(f"  [dim]- {a}[/dim]")
            console.print()
    table = Table(box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Op.", style="bold yellow", width=6)
    table.add_column("Hipodromo")
    idx = 1
    for hipodromo in disponibles:
        label = hipodromo.replace("_", " ").title()
        table.add_row(str(idx), label)
        idx += 1
    table.add_row("0", "Cancelar")
    console.print(table)
    opcion = Prompt.ask("\n[bold]Seleccione el hipodromo a comparar[/bold]", default="")
    try:
        num = int(opcion)
        if num == 0:
            return None
        if 1 <= num <= len(disponibles):
            return disponibles[num - 1]
    except ValueError:
        pass
    return None


def menu_principal() -> int:
    limpiar_pantalla()
    console.rule("[bold]CONTROL COMPARADOR[/bold]")
    table = Table(box=box.HEAVY, header_style="bold cyan")
    table.add_column("Op.", style="bold yellow", width=6)
    table.add_column("Hipodromo")
    table.add_row("1", "SAN ISIDRO")
    table.add_row("2", "PALERMO")
    table.add_row("3", "LA PLATA")
    table.add_row("4", "AUTO-DETECT (carpeta)")
    table.add_row("5", "Salir")
    console.print(table)
    opcion = Prompt.ask("\n[bold]Seleccione el hipodromo[/bold]", default="")
    try:
        return int(opcion)
    except ValueError:
        return 0
