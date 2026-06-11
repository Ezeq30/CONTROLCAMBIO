# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional


def parsear_monto_str(valor_str: Optional[str]) -> Optional[float]:
    """Convierte un string de monto a float, aceptando:
    - Punto como separador de miles: "5.000" -> 5000.0
    - Coma como decimal europeo: "1000,50" -> 1000.5
    - Formato mixto: "1.000,50" -> 1000.5
    Retorna None si no se puede parsear.
    """
    if not valor_str or not isinstance(valor_str, str):
        return None
    s = valor_str.strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    if "." in s:
        partes = s.split(".")
        if len(partes) >= 2 and all(p.isdigit() for p in partes) and len(partes[-1]) == 3:
            try:
                return float(s.replace(".", ""))
            except ValueError:
                pass
        try:
            return float(s)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None
