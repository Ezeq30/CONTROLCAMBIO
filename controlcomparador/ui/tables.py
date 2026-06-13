# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from rich.table import Table

from rich import box

from controlcomparador.config import ORDEN_APUESTAS, SYM_OK, SYM_FAIL
from controlcomparador.ui.console import console


def _ordenar_codigos(codigos: set[str]) -> list[str]:
    def key(cod):
        try:
            return (0, ORDEN_APUESTAS.index(cod))
        except ValueError:
            return (1, cod)
    return sorted(codigos, key=key)


def formato_valor(v: Optional[float]) -> str:
    if v is None:
        return "-"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.2f}"


def _estado_apuesta(v1: Optional[float], v2: Optional[float], etiq1: str, etiq2: str) -> str:
    if v1 == v2:
        return f"[green]{SYM_OK}[/green]"
    if v1 is None:
        return f"[yellow]solo {etiq2}[/yellow]"
    if v2 is None:
        return f"[yellow]solo {etiq1}[/yellow]"
    return f"[red]{SYM_FAIL}[/red]"


def imprimir_tabla_san_isidro(
    datos_pdf: dict,
    datos_reporte: dict,
    datos_posting: Optional[tuple[dict, set[str]]] = None,
    fecha_reporte: Optional[str] = None,
    tipo_pdf: Optional[str] = None,
) -> None:
    valores_posting = datos_posting[0] if datos_posting else {}
    if fecha_reporte:
        console.print(f"[info]Fecha del reporte: {fecha_reporte}[/info]")

    label_pdf = tipo_pdf or "OFICIAL"
    console.rule(f"[bold]COMPARACION {label_pdf} vs REPORTE[/bold]")
    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column(label_pdf, justify="right", width=10)
    t.add_column("Reporte", justify="right", width=10)
    if datos_posting:
        t.add_column("Posting", justify="right", width=10)
    t.add_column("Estado", justify="center", width=10)

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
            estado = _estado_apuesta(v_pdf, v_rep, label_pdf.lower(), "reporte")
            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""
            row = [carrera_str, cab_show, cod, formato_valor(v_pdf), formato_valor(v_rep)]
            if datos_posting:
                row.append(formato_valor(pos_ap.get(cod)))
            row.append(estado)
            t.add_row(*row)

    console.print(t)
    console.print()


def imprimir_tablas_palermo(
    datos_pdf: dict,
    datos_reporte: tuple,
    fechas: list[str],
    fecha_usada: Optional[str],
    datos_posting: Optional[tuple[dict, set[str]]] = None,
) -> None:
    valores_reporte, codigos_all = datos_reporte
    valores_posting = datos_posting[0] if datos_posting else {}
    if fechas:
        console.print(f"[info]Fechas detectadas: {', '.join(fechas)}[/info]")
    if fecha_usada:
        console.print(f"[info]Fecha usada: {fecha_usada}[/info]")

    console.rule("[bold]COMPARACION BASES PALERMO vs REPORTE[/bold]")
    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column("Bases Palermo", justify="right", width=10)
    if datos_posting:
        t.add_column("Posting", justify="right", width=10)
    t.add_column("Reporte", justify="right", width=10)
    t.add_column("Estado", justify="center", width=10)

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
            estado = _estado_apuesta(v_bases, v_rep, "bases", "reporte")
            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""
            row = [carrera_str, cab_show, cod, formato_valor(v_bases)]
            if datos_posting:
                row.append(formato_valor(pos_ap.get(cod)))
            row.extend([formato_valor(v_rep), estado])
            t.add_row(*row)

    console.print(t)
    console.print()


def imprimir_tabla_laplata(
    datos_planilla: dict,
    datos_reporte: dict,
    datos_posting: Optional[tuple[dict, set[str]]] = None,
) -> None:
    valores_posting = datos_posting[0] if datos_posting else {}

    console.rule("[bold]COMPARACION PLANILLA vs REPORTE - LA PLATA[/bold]")
    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column("Planilla", justify="right", width=10)
    if datos_posting:
        t.add_column("Posting", justify="right", width=10)
    t.add_column("Reporte", justify="right", width=10)
    t.add_column("Estado", justify="center", width=10)

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

        todos_codigos = _ordenar_codigos(set(ap_plan.keys()) | set(ap_rep.keys()))
        for idx, cod in enumerate(todos_codigos):
            v_plan = ap_plan.get(cod)
            v_rep = ap_rep.get(cod)
            estado = _estado_apuesta(v_plan, v_rep, "planilla", "reporte")
            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = cab_str if idx == 0 else ""
            row = [carrera_str, cab_show, cod, formato_valor(v_plan)]
            if datos_posting:
                row.append(formato_valor(pos_ap.get(cod)))
            row.extend([formato_valor(v_rep), estado])
            t.add_row(*row)

    console.print(t)
    console.print()


def imprimir_tabla_posting_vs_reporte(
    datos_posting: tuple[dict, set[str]],
    datos_reporte: tuple[dict, set[str]],
) -> None:
    valores_posting, _ = datos_posting
    valores_reporte, _ = datos_reporte

    console.rule("[bold]COMPARACION POSTING vs REPORTE[/bold]")
    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column("Posting", justify="right", width=10)
    t.add_column("Reporte", justify="right", width=10)
    t.add_column("Estado", justify="center", width=10)

    todas = sorted(set(valores_posting.keys()) | set(valores_reporte.keys()))
    for num_carrera in todas:
        pos_ap = valores_posting.get(num_carrera, {})
        rep_ap = valores_reporte.get(num_carrera, {})
        codigos = _ordenar_codigos(set(pos_ap.keys()) | set(rep_ap.keys()))
        for idx, cod in enumerate(codigos):
            v_pos = pos_ap.get(cod)
            v_rep = rep_ap.get(cod)
            estado = _estado_apuesta(v_pos, v_rep, "posting", "reporte")
            carrera_str = str(num_carrera) if idx == 0 else ""
            t.add_row(carrera_str, cod, formato_valor(v_pos), formato_valor(v_rep), estado)

    console.print(t)
    console.print()


def _validar_apuestas_tela(datos: dict[int, dict]) -> list[tuple[int, int, str]]:
    warnings: list[tuple[int, int, str]] = []
    for num_carrera in sorted(datos.keys()):
        d = datos[num_carrera]
        cab = d.get("caballos", 0)
        apuestas = set(d.get("apuestas", {}).keys())

        if cab < 8 and "TER" in apuestas:
            warnings.append((num_carrera, cab, "TER no debería estar"))

        if cab >= 12:
            if "IMP" not in apuestas:
                warnings.append((num_carrera, cab, "IMP debería estar"))
            if "EXA" in apuestas:
                warnings.append((num_carrera, cab, "EXA no debería estar"))

        if cab <= 11:
            if "EXA" not in apuestas:
                warnings.append((num_carrera, cab, "EXA debería estar"))
            if "IMP" in apuestas:
                warnings.append((num_carrera, cab, "IMP no debería estar"))

        if cab == 4:
            if "SEG" in apuestas:
                warnings.append((num_carrera, cab, "SEG no debería estar"))
            if "TRI" in apuestas:
                warnings.append((num_carrera, cab, "TRI no debería estar"))
            if "CUA" in apuestas:
                warnings.append((num_carrera, cab, "CUA no debería estar"))

        if "EXA" in apuestas and "IMP" in apuestas:
            warnings.append((num_carrera, cab, "EXA e IMP no pueden estar juntos"))

        if "TRI" in apuestas and "CUA" in apuestas:
            warnings.append((num_carrera, cab, "TRI y CUA no pueden estar juntos"))

    return warnings


def _mostrar_validaciones(warnings: list[tuple[int, int, str]]) -> None:
    if not warnings:
        console.print("[green]OK[/green]\n")
        return

    t = Table(box=box.SIMPLE, header_style="bold", title="[bold]VALIDACIONES[/bold]")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Observación", width=60)

    grouped: dict[tuple[int, int], list[str]] = {}
    for num, cab, msg in warnings:
        grouped.setdefault((num, cab), []).append(msg)

    for (num, cab), msgs in sorted(grouped.items()):
        t.add_row(str(num), str(cab), " / ".join(msgs))

    console.print(t)
    console.print()


def _format_carreras_list(carreras: list[int], total: int) -> str:
    if len(carreras) == total:
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


def _mostrar_bases_por_apuesta(datos: dict[int, dict]) -> None:
    grupos: dict[tuple[str, float | None], list[int]] = {}
    for num_carrera in sorted(datos.keys()):
        d = datos[num_carrera]
        apuestas = d.get("apuestas", {})
        for cod, val in apuestas.items():
            grupos.setdefault((cod, val), []).append(num_carrera)

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
        t.add_row(str(idx), _format_carreras_list(carreras, total), cod, formato_valor(val))

    console.print(t)
    console.print()


def imprimir_resumen_tela(datos: dict[int, dict], ruta: str) -> None:
    total_carreras = len(datos)
    total_apuestas = sum(len(d.get("apuestas", {})) for d in datos.values())

    console.rule("[bold]RESUMEN TELA OFICIAL[/bold]")
    console.print(f"  [dim]Archivo:[/dim] {ruta}")
    console.print(f"  [cyan]Carreras:[/cyan] {total_carreras}  |  [cyan]Apuestas:[/cyan] {total_apuestas}\n")

    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Carrera", style="yellow", width=6)
    t.add_column("Caballos", justify="center", width=8)
    t.add_column("Apuesta", style="cyan", width=8)
    t.add_column("Valor", justify="right", width=10)

    for num_carrera in sorted(datos.keys()):
        d = datos[num_carrera]
        cab = d.get("caballos", 0)
        apuestas = d.get("apuestas", {})
        codigos = _ordenar_codigos(set(apuestas.keys()))
        for idx, cod in enumerate(codigos):
            val = apuestas.get(cod)
            carrera_str = str(num_carrera) if idx == 0 else ""
            cab_show = str(cab) if idx == 0 else ""
            t.add_row(carrera_str, cab_show, cod, formato_valor(val))

    console.print(t)
    console.print()

    warnings = _validar_apuestas_tela(datos)
    _mostrar_validaciones(warnings)
    _mostrar_bases_por_apuesta(datos)


def mostrar_resumen_comparacion(coincide: bool, diferencias: list[str], titulo: str = "COMPARACION") -> None:
    if coincide:
        console.print(f"\n[bold green]{SYM_OK} {titulo}: todo coincide correctamente.[/bold green]\n")
    else:
        console.print(f"\n[bold red]{SYM_FAIL} {titulo}: se encontraron diferencias:[/bold red]")
        for d in diferencias:
            console.print(f"  [yellow]- {d}[/yellow]")
        console.print()



