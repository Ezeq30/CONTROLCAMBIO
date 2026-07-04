# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich import box

from controlcomparador.control_xml.detector import TipoXmlHipodromo, detectar_tipo_xml
from controlcomparador.control_xml.models import ResultadoControlXml
from controlcomparador.control_xml.parsers import hsi, la_plata
from controlcomparador.ui.console import console


def controlar_xml(ruta: str | Path) -> ResultadoControlXml:
    path = Path(ruta)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    tipo = detectar_tipo_xml(path)
    if tipo == TipoXmlHipodromo.HSI:
        return hsi.parsear(path)
    if tipo == TipoXmlHipodromo.LA_PLATA:
        return la_plata.parsear(path)
    raise ValueError(
        "XML no reconocido; use un archivo ARG_HSI_* (San Isidro) o ARG_LP_* (La Plata)."
    )


def imprimir_control_xml(resultado: ResultadoControlXml) -> None:
    console.print(f"[bold]{resultado.hipodromo}[/bold]")
    if resultado.fecha:
        console.print(f"Fecha: {resultado.fecha}")
    console.print(f"Total carreras: {len(resultado.carreras)}")
    console.print()

    tabla = Table(box=box.SIMPLE, show_header=True, header_style="bold #2e7d32")
    tabla.add_column("Carrera", justify="right", style="cyan")
    tabla.add_column("Caballos", justify="right")
    for nro, caballos in resultado.carreras:
        tabla.add_row(str(nro), str(caballos))
    console.print(tabla)
    console.print()
