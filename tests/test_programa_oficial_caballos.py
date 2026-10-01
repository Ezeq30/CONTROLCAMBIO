# -*- coding: utf-8 -*-
"""Conteo de caballos del REPORTE PROGRAMA OFICIAL (una carrera por página)."""

from pathlib import Path

import pytest

from controlcomparador.parsers.pdf import (
    _caballos_bloque_programa_oficial,
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)

FIXTURE_8250 = Path(__file__).parent / "fixtures" / "programa_oficial_si_8250.pdf"


def _grilla(n: int) -> list[str]:
    return [
        f"STUD X{i} (AR) 1SI-2SI-3SI {i:02d} CABALLO{i} JOCKEY{i} ENTRENADOR{i} Z - 5 - PADRE - MADRE"
        for i in range(1, n + 1)
    ]


def _chaquetillas(nums: list[int]) -> str:
    return "CHAQUETILLAS: " + " ".join(f"- {n:02d} - azul,g.bca." for n in nums)


class TestCaballosPagina:
    def test_chaquetillas_completo(self):
        lineas = ["16:45 hs", *_grilla(7), "SUPLENTES", _chaquetillas(list(range(1, 8))),
                  "7a CLÁSICO RESUELLO", "APUESTAS", "Exacta $2.000"]
        assert _caballos_bloque_programa_oficial(lineas) == 7

    def test_chaquetillas_en_varias_lineas(self):
        lineas = [
            *_grilla(9),
            "SUPLENTES",
            _chaquetillas([1, 2, 3, 4, 5]),
            "- 06 - oro - 07 - verde - 08 - neg. - 09 - bca.",
            "1a PREMIO EJEMPLO",
        ]
        assert _caballos_bloque_programa_oficial(lineas) == 9

    def test_chaquetillas_gana_si_grilla_pierde_dorsales(self):
        """pypdf pega dorsales a otros tokens: la grilla no los ve, CHAQUETILLAS sí."""
        lineas = [
            "STUD AAA01CABALLOPEGADO",
            "STUD BBB02CABALLOPEGADO",
            "SUPLENTES",
            _chaquetillas(list(range(1, 10))),
        ]
        assert _caballos_bloque_programa_oficial(lineas) == 9

    def test_suplentes_con_dorsal_mayor_no_cuentan(self):
        lineas = [
            *_grilla(7),
            "SUPLENTES",
            "STUD S (AR) 1SI 08 SUPLENTE OCHO JOCKEY ENTRENADOR",
            _chaquetillas(list(range(1, 9))),
        ]
        assert _caballos_bloque_programa_oficial(lineas) == 7

    def test_suplentes_numerados_desde_01_no_pisan_titulares(self):
        lineas = [
            *_grilla(8),
            "SUPLENTES",
            "STUD S (AR) 1SI 01 RICHARD JOCKEY ENTRENADOR",
            "STUD S (AR) 1SI 02 MUST NOT JOCKEY ENTRENADOR",
            _chaquetillas(list(range(1, 9))),
        ]
        assert _caballos_bloque_programa_oficial(lineas) == 8

    def test_sin_chaquetillas_usa_grilla(self):
        lineas = [*_grilla(6), "SUPLENTES", "STUD S (AR) 1SI 07 SUPLENTE JOCKEY"]
        assert _caballos_bloque_programa_oficial(lineas) == 6

    def test_dorsal_pegado_a_ultimas(self):
        lineas = [
            "LAS 3 SEMILLAS (SR)4AR-1AR-2SI-0AR01 ANA DE ARMAS LARREA FRUTOS",
            "LA AGUADA (VM) 1LP-1LP-1LP 02 WANDA VILLAGRA JUAN CRUZ",
        ]
        assert _caballos_bloque_programa_oficial(lineas) == 2

    def test_pagina_sin_caballos(self):
        assert _caballos_bloque_programa_oficial(["APUESTAS", "Exacta $2.000"]) is None


@pytest.mark.skipif(not FIXTURE_8250.exists(), reason="fixture PDF 8250 ausente")
class TestPdf8250:
    def test_mapa_caballos(self):
        """Bug: C7 daba 6 (dorsal 07 con coordenadas rotas en pypdf)."""
        esperado = {
            1: 9, 2: 6, 3: 9, 4: 9, 5: 7, 6: 9,
            7: 7, 8: 9, 9: 9, 10: 9, 11: 11, 12: 12,
        }
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_8250))
        assert {n: d["caballos"] for n, d in datos.items()} == esperado

    def test_rechaza_pdf_que_no_es_programa_oficial(self, tmp_path):
        falso = tmp_path / "otro.pdf"
        falso.write_bytes(b"%PDF-1.4\n%%EOF")
        with pytest.raises(ValueError):
            obtener_apuestas_por_carrera(falso)
