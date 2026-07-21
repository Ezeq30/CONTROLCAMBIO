# -*- coding: utf-8 -*-
"""Regresión: 2 carreras en la misma página de tela (PDF SI 25-07-2026 C7/C8).

Bug: buscar el nro de carrera hacia atrás tomaba el de la carrera anterior,
mezclando caballos (5→11) y pisando pases (Cadena Ultimo Pase perdido).
También 'Cuaterna Selectiva' no matcheaba (solo 'Selectivo').
"""

from controlcomparador.config import PATRON_PASE_TELA
from controlcomparador.parsers.pdf import (
    _contar_caballos_tela,
    _numero_carrera_tela,
    _normalizar_pase,
    abreviar_apuesta,
)


def _linea_caballo(nro: int, nombre: str) -> str:
    return f"Stud Test (LP)  0S-  -  -  {nro}  {nombre}    57.0 Jockey Name Trainer Z. 5 Sire Dam"


# Página con C7 (5 caballos + Cadena Ultimo) y C8 (11 caballos), como el PDF real.
_PAGINA_DOS_CARRERAS = [
    "Premio BAYAKOA (L)",
    "APUESTAS: Ganador, Segundo $ 2, Exacta $ 2000, Trifecta $ 2000STUD 4 ULTIMAS CABALLO JOCKEY ENTRENADOR",
    "Bolsa Total: $ 22500080",
    " Total de Premios al 1: $ 11250000  al 2: $ 3937500",
    "Triplo 2do.Pase, Cuaterna Selectiva 1er.Pase $2000, Cuaterna 3er.Pase, "
    "Quintuplo 4to.Pase, Cadena Con Jackpot Ultimo Pase, Doble $2000",
    " 7 ",
    "15:50 hs.",
    _linea_caballo(1, "GOTA"),
    _linea_caballo(2, "LIDA"),
    _linea_caballo(3, "JUST"),
    _linea_caballo(4, "RUBY"),
    _linea_caballo(5, "HI"),
    " CHAQUETILLAS:  -  1 - azul -  2 - gran -  3 - azul -  4 - azl -  5 - oro",
    "Premio BLUES TRAVELER 2014",
    "APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000, Cuatrifecta $ 1000STUD 4 ULTIMAS CABALLO JOCKEY",
    "Bolsa Total: $ 9265000",
    "Triplo 1er.Pase $5000, Triplo Ultimo Pase, Cuaterna Selectiva 2do.Pase, "
    "Cuaterna Ultimo Pase, Quintuplo Ultimo Pase, Doble $2000",
    " 8 ",
    "16:20 hs.",
    *[_linea_caballo(i, f"H{i}") for i in range(1, 12)],
    " CHAQUETILLAS:  -  1 - a -  2 - b",
]


class TestNumeroCarreraDosEnMismaPagina:
    def test_carrera_8_no_toma_numero_7(self):
        paginas = [_PAGINA_DOS_CARRERAS]
        # Bloque C8: desde su APUESTAS hasta fin
        start = _PAGINA_DOS_CARRERAS.index(
            "APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000, Cuatrifecta $ 1000STUD 4 ULTIMAS CABALLO JOCKEY"
        )
        race_lines = _PAGINA_DOS_CARRERAS[start:]
        assert _numero_carrera_tela(paginas, 0, start, race_lines) == 8

    def test_carrera_7_correcta(self):
        paginas = [_PAGINA_DOS_CARRERAS]
        start = 1  # APUESTAS C7
        end = _PAGINA_DOS_CARRERAS.index(
            "APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000, Cuatrifecta $ 1000STUD 4 ULTIMAS CABALLO JOCKEY"
        )
        race_lines = _PAGINA_DOS_CARRERAS[start:end]
        assert _numero_carrera_tela(paginas, 0, start, race_lines) == 7
        assert _contar_caballos_tela(race_lines) == 5


class TestPaseSelectivaYCadenaUltimo:
    def test_selectiva_1er_pase(self):
        texto = "Cuaterna Selectiva 1er.Pase $2000"
        matches = list(PATRON_PASE_TELA.finditer(texto))
        assert len(matches) == 1
        assert matches[0].group(1).lower() == "cuaterna"
        assert "1er" in matches[0].group(2).lower()

    def test_cadena_con_jackpot_ultimo_pase(self):
        texto = (
            "Triplo 2do.Pase, Cuaterna Selectiva 1er.Pase $2000, Cuaterna 3er.Pase, "
            "Quintuplo 4to.Pase, Cadena Con Jackpot Ultimo Pase, Doble $2000"
        )
        por_codigo: dict[str, set[str]] = {}
        for m in PATRON_PASE_TELA.finditer(texto):
            cod = abreviar_apuesta(m.group(1).lower())
            por_codigo.setdefault(cod, set()).add(_normalizar_pase(m.group(2)))
        assert "Ultimo Pase" in por_codigo.get("CAD", set())
        assert "1er.Pase" in por_codigo.get("QTN", set())
        assert "3er.Pase" in por_codigo.get("QTN", set())
        assert "4to.Pase" in por_codigo.get("QTP", set())
        assert "2do.Pase" in por_codigo.get("TPL", set())
