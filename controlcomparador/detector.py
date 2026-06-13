from __future__ import annotations

from pathlib import Path
from typing import Optional

from controlcomparador.config import (
    PATRON_CARRERA_PDF,
    PATRON_FILA_PALERMO,
    PATRON_APUESTAS_A,
    PATRON_PROGRAMA_DEPURADO,
)


HIPODROMOS = ["san_isidro", "palermo", "la_plata"]


def _clasificar_pdf(ruta: Path) -> Optional[str]:
    import pypdf
    try:
        reader = pypdf.PdfReader(ruta)
        texto = ""
        for i in range(min(3, len(reader.pages))):
            texto += (reader.pages[i].extract_text() or "") + "\n"
    except Exception:
        return None

    tiene_fila_palermo = bool(PATRON_FILA_PALERMO.search(texto))
    tiene_apuestas_a = bool(PATRON_APUESTAS_A.search(texto))
    tiene_carrera_pdf = bool(PATRON_CARRERA_PDF.search(texto))
    tiene_programa_depurado = bool(PATRON_PROGRAMA_DEPURADO.search(texto))

    if tiene_carrera_pdf or tiene_programa_depurado:
        return "san_isidro"
    if tiene_fila_palermo:
        return "palermo_bases"
    if tiene_apuestas_a:
        return "palermo_oficial"
    return "pdf_desconocido"


def _clasificar_txt(ruta: Path) -> Optional[str]:
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            cabecera = f.read(50000)
    except Exception:
        return None

    tiene_rsm = "RSM TABLE" in cabecera
    tiene_posting = "CARD POSTING PRICES" in cabecera

    if tiene_rsm:
        return "reporte"
    if tiene_posting:
        return "posting"
    return None


def _clasificar_xls(ruta: Path) -> Optional[str]:
    return "planilla_laplata"


def _tipo_archivo(ruta: Path) -> Optional[str]:
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        return _clasificar_pdf(ruta)
    if ext == ".txt":
        return _clasificar_txt(ruta)
    if ext == ".xls":
        return _clasificar_xls(ruta)
    return None


def detectar_archivos(ruta_carpeta: str | Path) -> dict:
    carpeta = Path(ruta_carpeta)
    if not carpeta.is_dir():
        return {"error": "La ruta no es una carpeta valida"}

    resultado: dict[str, dict] = {
        "san_isidro": {"pdf": None, "reporte": None, "posting": []},
        "palermo": {"bases_pdf": None, "oficial_pdf": None, "reporte": None, "posting": []},
        "la_plata": {"planilla": None, "reporte": None, "posting": []},
    }
    desconocidos: list[str] = []

    for archivo in sorted(carpeta.iterdir()):
        if not archivo.is_file():
            continue
        tipo = _tipo_archivo(archivo)
        if tipo is None:
            continue

        if tipo == "san_isidro":
            resultado["san_isidro"]["pdf"] = archivo
        elif tipo == "palermo_bases":
            resultado["palermo"]["bases_pdf"] = archivo
        elif tipo == "palermo_oficial":
            resultado["palermo"]["oficial_pdf"] = archivo
        elif tipo == "reporte":
            resultado["san_isidro"]["reporte"] = archivo
            resultado["palermo"]["reporte"] = archivo
            resultado["la_plata"]["reporte"] = archivo
        elif tipo == "posting":
            resultado["san_isidro"]["posting"].append(archivo)
            resultado["palermo"]["posting"].append(archivo)
            resultado["la_plata"]["posting"].append(archivo)
        elif tipo == "planilla_laplata":
            resultado["la_plata"]["planilla"] = archivo
        else:
            desconocidos.append(archivo.name)

    return resultado


def hipodromos_detectados(deteccion: dict) -> list[str]:
    detectados: list[str] = []
    for hipodromo in HIPODROMOS:
        info = deteccion.get(hipodromo, {})
        if hipodromo == "san_isidro":
            if info.get("pdf") and info.get("reporte"):
                detectados.append("san_isidro")
        elif hipodromo == "palermo":
            if info.get("bases_pdf") and info.get("reporte"):
                detectados.append("palermo")
        elif hipodromo == "la_plata":
            if info.get("planilla") and info.get("reporte"):
                detectados.append("la_plata")
    return detectados


def resumen_deteccion(deteccion: dict) -> dict[str, list[str]]:
    resumen: dict[str, list[str]] = {}
    for hipodromo in HIPODROMOS:
        info = deteccion.get(hipodromo, {})
        archivos: list[str] = []
        for key, val in info.items():
            if isinstance(val, list):
                for v in val:
                    if v:
                        archivos.append(v.name)
            elif val:
                archivos.append(val.name)
        if archivos:
            label = hipodromo.replace("_", " ").title()
            resumen[label] = archivos
    return resumen
