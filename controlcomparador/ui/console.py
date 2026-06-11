# -*- coding: utf-8 -*-

from rich.console import Console
from rich.theme import Theme

tema = Theme({
    "ok": "bold green",
    "fail": "bold red",
    "info": "bold blue",
    "warn": "bold yellow",
    "title": "bold white on blue",
    "diff": "bold yellow",
    "carrera": "bold cyan",
    "codigo": "bold magenta",
})

console = Console(theme=tema)
