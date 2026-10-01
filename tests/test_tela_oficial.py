# -*- coding: utf-8 -*-

import pytest

from controlcomparador.parsers.pdf import es_apuesta_excluida


class TestEsApuestaExcluida:
  @pytest.mark.parametrize(
      "nombre,debe_excluir",
      [
          ("Cuaterna último Pase", True),
          ("Cuaterna ltimo Pase", True),
          ("Cuaternaltimo Pase", True),
          ("Cuaterna \u00datimo Pase", True),
          ("Cuaterna \u00daltimo Pase", True),
          ("Triplo Final Ultimo Pase", True),
          ("Cuaterna Final \u00daltimo Pase", True),
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
          ("Cuaterna Selectiva 1er.Pase $2000", False),
          ("Doble $2000", False),
          ("Exacta $ 2000", False),
          ("Doble último pase", True),
          ("Doble 2° Pase", True),
          ("Doble 1° Pase $2000", False),
      ],
  )
  def test_exclusion_pases(self, nombre, debe_excluir):
      assert es_apuesta_excluida(nombre) is debe_excluir
