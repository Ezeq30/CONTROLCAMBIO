# -*- coding: utf-8 -*-

import pytest

from controlcomparador.config import APUESTAS_PICK
from controlcomparador.parsers.pdf import (
    es_apuesta_excluida,
    _parsear_bets_tela,
    obtener_apuestas_por_carrera,
    normalizar_desde_lista_apuestas,
)


class TestEsApuestaExcluida:
  @pytest.mark.parametrize(
      "nombre,debe_excluir",
      [
          ("Cuaterna último Pase", True),
          ("Cuaterna ltimo Pase", True),
          ("Cuaternaltimo Pase", True),
          ("Cadena Con Jackpot Último Pase", True),
          ("Cadena Con Jackpot Iltimo Pase", True),
          ("Triplo Selectivo último Pase", True),
          ("Triplo Selectivo ltimo Pase", True),
          ("Quintuplo último Pase", True),
          ("Cuaterna 2do.Pase", True),
          ("Cuaterna 3er.Pase", True),
          ("Cadena Con Jackpot 5to.Pase", True),
          ("Cadena Con Jackpot 6to.Pase", True),
          ("Cuaterna 1er.Pase $2000", False),
          ("Triplo 1er.Pase $2000", False),
          ("Quintuplo 1er.Pase $1000", False),
          ("Triplo Selectivo 1er.Pase $5000", False),
          ("Doble $2000", False),
          ("Exacta $ 2000", False),
      ],
  )
  def test_exclusion_pases(self, nombre, debe_excluir):
      assert es_apuesta_excluida(nombre) is debe_excluir


class TestParsearBetsTela:
  def test_extra_linea_carrera_4_sin_picks_fantasma(self):
      extra = (
          "Cuaterna Con Jackpot 2do.Pase, Cuaterna último Pase, "
          "Quintuplo 1er.Pase $1000, Cadena Con Jackpot 3er.Pase, Doble $2000"
      )
      parsed = dict(_parsear_bets_tela(extra))
      assert parsed.get("QTP") == "1000"
      assert parsed.get("DOB") == "2000"
      assert "QTN" not in parsed
      assert "CAD" not in parsed

  def test_extra_linea_carrera_8_sin_ultimo_pase(self):
      extra = (
          "Triplo Selectivo 1er.Pase $5000, Triplo último Pase, "
          "Cuaterna 2do.Pase, Cuaterna último Pase, Quintuplo último Pase, Doble $2000"
      )
      parsed = dict(_parsear_bets_tela(extra))
      assert parsed.get("TPL") == "5000"
      assert parsed.get("DOB") == "2000"
      assert "QTN" not in parsed
      assert "QTP" not in parsed

  def test_encoding_corrupto_como_pdf(self):
      extra = (
          "Triplo Selectivo \ufffdltimo Pase, Cuaterna 1er.Pase $2000, "
          "Cuaterna \ufffdltimo Pase, Quintuplo 2do.Pase, Doble $2000"
      )
      parsed = dict(_parsear_bets_tela(extra))
      assert parsed.get("QTN") == "2000"
      assert parsed.get("DOB") == "2000"
      assert "TPL" not in parsed


@pytest.mark.skipif(
    not __import__("pathlib").Path(
        r"c:\Users\cdiaz\Downloads\SI_PROGRAMA_OFICIAL_01-07-2026_7922.pdf"
    ).is_file(),
    reason="PDF de integración no disponible",
)
class TestPdfIntegracion:
  PDF = r"c:\Users\cdiaz\Downloads\SI_PROGRAMA_OFICIAL_01-07-2026_7922.pdf"

  def test_sin_picks_fantasma_en_carreras_problematicas(self):
      datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(self.PDF))
      esperado = {
          4: {"QTP": 1000.0},
          6: {"TPL": 2000.0},
          7: {"QTN": 2000.0},
          8: {"TPL": 5000.0},
          10: {"QTN": 2000.0},
      }
      for carrera, picks_ok in esperado.items():
          picks = {
              k: v
              for k, v in datos[carrera]["apuestas"].items()
              if k in APUESTAS_PICK
          }
          assert picks == picks_ok, f"Carrera {carrera}: {picks} != {picks_ok}"
