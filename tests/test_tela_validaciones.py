# -*- coding: utf-8 -*-

from controlcomparador.ui.tables import (
    MSG_EXA_IMP_JUNTOS,
    MSG_TRI_CUA_JUNTOS,
    _html_panel_reglas,
    _html_panel_validaciones,
    _REGLAS_PARES_VALIDACION_TELA,
    _REGLAS_VALIDACION_TELA,
    _validar_carreras_tela,
)


def _datos(*items):
    """items: (nro_carrera, caballos, lista_apuestas)"""
    return {
        n: {"caballos": cab, "apuestas": dict(apuestas)}
        for n, cab, apuestas in items
    }


class TestValidarCarrerasTela:
    def test_carrera_ok_sin_violaciones(self):
        datos = _datos((1, 10, [("EXA", 2000), ("GAN", None), ("TER", None)]))
        cab, violaciones = _validar_carreras_tela(datos)[1]
        assert cab == 10
        assert violaciones == []

    def test_exa_y_tri_sin_violacion_pares(self):
        datos = _datos((1, 10, [("EXA", 2000), ("TRI", 2000), ("TER", None)]))
        _, violaciones = _validar_carreras_tela(datos)[1]
        assert not any(MSG_EXA_IMP_JUNTOS in v[0] for v in violaciones)
        assert not any(MSG_TRI_CUA_JUNTOS in v[0] for v in violaciones)

    def test_tri_y_cua_juntos(self):
        datos = _datos((4, 14, [("TRI", 2000), ("CUA", 1000), ("TER", None)]))
        _, violaciones = _validar_carreras_tela(datos)[4]
        assert any(v[0] == MSG_TRI_CUA_JUNTOS for v in violaciones)

    def test_once_caballos_exa_imp_reglas(self):
        datos = _datos((13, 11, [("IMP", 5000), ("TER", None)]))
        _, violaciones = _validar_carreras_tela(datos)[13]
        assert len(violaciones) == 2
        assert violaciones[0] == (
            "EXA debería estar",
            "≤ 11 caballos → EXA obligatorio",
        )
        assert violaciones[1] == (
            "IMP no debería estar",
            "≤ 11 caballos → sin IMP",
        )

    def test_doce_caballos_imp_obligatorio_sin_exa(self):
        datos = _datos((1, 12, [("EXA", 2000), ("TER", None)]))
        _, violaciones = _validar_carreras_tela(datos)[1]
        obs = [v[0] for v in violaciones]
        reglas = [v[1] for v in violaciones]
        assert "IMP debería estar" in obs
        assert "EXA no debería estar" in obs
        assert "≥ 12 caballos → IMP obligatorio" in reglas
        assert "≥ 12 caballos → sin EXA" in reglas

    def test_ocho_caballos_ter_obligatorio(self):
        datos = _datos((1, 8, [("EXA", 2000), ("GAN", None)]))
        _, violaciones = _validar_carreras_tela(datos)[1]
        assert any(v == ("TER debería estar", "≥ 8 caballos → TER obligatorio") for v in violaciones)

    def test_siete_caballos_sin_ter_ok(self):
        datos = _datos((2, 7, [("EXA", 2000), ("GAN", None)]))
        _, violaciones = _validar_carreras_tela(datos)[2]
        assert not any("TER" in v[0] for v in violaciones)

    def test_html_reglas_pares_en_fila(self):
        datos = _datos(
            (1, 10, [("EXA", 2000), ("TER", None)]),
            (4, 14, [("TRI", 2000), ("CUA", 1000), ("TER", None)]),
        )
        html = _html_panel_reglas()
        assert "panel-reglas" in html
        assert "reglas-table" in html
        assert "≥ 8 caballos → TER obligatorio" in html
        assert f"<td class=\"reglas-par\">{_REGLAS_PARES_VALIDACION_TELA[0]}</td>" in html
        assert f"<td class=\"reglas-par\">{_REGLAS_PARES_VALIDACION_TELA[1]}</td>" in html
        assert "son excluyentes" not in html
        html_val = _html_panel_validaciones(_validar_carreras_tela(datos))
        assert MSG_TRI_CUA_JUNTOS in html_val
        assert 'class="warn"' in html_val
        assert len(_REGLAS_VALIDACION_TELA) == 8
        # Una fila por regla de caballos/pick + 2 de pares
        assert html.count("<tr><td") == len(_REGLAS_VALIDACION_TELA) + 2
