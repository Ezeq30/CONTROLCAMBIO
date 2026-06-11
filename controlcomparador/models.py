# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Apuesta:
    codigo: str
    valor: Optional[float] = None


@dataclass
class Carrera:
    numero: int
    nombre: str = ""
    caballos: int = 0
    apuestas: dict[str, Optional[float]] = field(default_factory=dict)


@dataclass
class DatosReporte:
    carreras: dict[int, Carrera] = field(default_factory=dict)

    def obtener(self, num_carrera: int) -> Optional[Carrera]:
        return self.carreras.get(num_carrera)

    def todas_las_carreras(self) -> list[int]:
        return sorted(self.carreras.keys())


@dataclass
class DatosPosting:
    valores_por_carrera: dict[int, dict[str, Optional[float]]] = field(default_factory=dict)
    codigos_con_all: set[str] = field(default_factory=set)


@dataclass
class ResultadoComparacion:
    coincide: bool
    diferencias: list[str] = field(default_factory=list)
    datos_origen: Optional[dict] = None
    datos_destino: Optional[dict] = None


@dataclass
class DatosPalermo:
    fechas: list[str] = field(default_factory=list)
    apuestas_por_fecha: dict[str, dict[int, dict[str, Optional[float]]]] = field(default_factory=dict)
    resumen_por_fecha: dict[str, dict[str, dict]] = field(default_factory=dict)


@dataclass
class ApuestaOficial:
    carrera: int
    apuestas: list[str] = field(default_factory=list)


@dataclass
class PostingMergeResult:
    valores_por_carrera: dict[int, dict[str, Optional[float]]] = field(default_factory=dict)
    codigos_con_all: set[str] = field(default_factory=set)
