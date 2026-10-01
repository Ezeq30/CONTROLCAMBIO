# -*- coding: utf-8 -*-
"""Regresión de pases: 'Cuaterna Selectiva', 'Cadena Con Jackpot Ultimo Pase', 'Jackpo t'."""

from controlcomparador.config import PATRON_PASE_TELA
from controlcomparador.parsers.pdf import (
    _normalizar_pase,
    abreviar_apuesta,
)


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

    def test_cuaterna_jackpo_t_ultimo_pase(self):
        """pypdf parte Jackpot como 'Jackpo t' — debe detectar Ultimo Pase QTN."""
        texto = (
            "Triplo 2do.Pase, Cuaterna 1er.Pase $2000, Cuaterna 3er.Pase, "
            "Cuaterna Con Jackpo t Ultimo Pase, Cadena Con Jackpot 5to.Pase, Doble $2000"
        )
        matches = list(PATRON_PASE_TELA.finditer(texto))
        por_codigo: dict[str, set[str]] = {}
        for m in matches:
            cod = abreviar_apuesta(m.group(1).lower())
            por_codigo.setdefault(cod, set()).add(_normalizar_pase(m.group(2)))
        assert "Ultimo Pase" in por_codigo.get("QTN", set())
        assert "5to.Pase" in por_codigo.get("CAD", set())
