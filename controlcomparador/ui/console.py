# -*- coding: utf-8 -*-
"""Consola Rich y utilidades de salida fija para vista par en Windows.

``escribir_salida_fija`` escribe directo con WriteConsoleW para que Rich no
reformatee líneas ya calculadas (evita huecos cuando la consola es más ancha
que el contenido). ``ampliar_consola_windows`` ajusta el buffer al ancho exacto
de las dos tablas pegadas antes de imprimir.
"""

from rich.console import Console
from rich.theme import Theme

# Tema alineado al HTML de tela oficial (#1b5e20)
tema = Theme({
    "ok": "bold green",
    "fail": "bold red",
    "info": "bold #2e7d32",
    "warn": "bold #e65100",
    "title": "bold white on #1b5e20",
    "diff": "bold yellow",
    "carrera": "bold cyan",
    "codigo": "bold #2e7d32",
    "header": "bold white on #1b5e20",
    "dimval": "dim",
    "accent": "#1b5e20",
})

console = Console(theme=tema)


def actualizar_ancho_consola() -> int:
    """Sincroniza ancho/alto de Rich con la consola real (menús interactivos)."""
    import shutil

    try:
        size = shutil.get_terminal_size(fallback=(120, 40))
    except OSError:
        return console.width or 120
    console.width = size.columns
    console.height = size.lines
    return size.columns


def ampliar_consola_windows(cols: int) -> None:
    """Amplía ventana/buffer de consola al ancho pedido (vista par posting)."""
    import sys

    if sys.platform != "win32" or cols < 1:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        kernel32.SetConsoleScreenBufferSize(handle, COORD(cols, 9001))
        rect = SMALL_RECT(0, 0, cols - 1, 49)
        kernel32.SetConsoleWindowInfo(handle, True, ctypes.byref(rect))
        console.width = cols
    except Exception:
        pass


def escribir_salida_fija(texto: str) -> None:
    """Escribe texto en consola sin reformato Rich (WriteConsoleW en Windows)."""
    import sys

    if not texto.endswith("\n"):
        texto = texto + "\n"
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            written = ctypes.c_ulong(0)
            ok = kernel32.WriteConsoleW(
                handle,
                texto,
                len(texto),
                ctypes.byref(written),
                None,
            )
            if ok:
                return
        except Exception:
            pass
    try:
        sys.stdout.buffer.write(texto.encode(sys.stdout.encoding or "utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    except Exception:
        sys.stdout.write(texto)
        sys.stdout.flush()
