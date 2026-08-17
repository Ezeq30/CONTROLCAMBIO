# -*- coding: utf-8 -*-

from controlcomparador.ui.tables import (
    MSG_EXA_IMP_JUNTOS,
    MSG_TRI_CUA_JUNTOS,
    _html_panel_reglas,
    _html_panel_validaciones,
    _REGLAS_PARES_VALIDACION_TELA,
    _REGLAS_VALIDACION_TELA,
    _validar_carreras_tela,
    mostrar_resumen_validaciones_tela,
    resumen_validaciones_tela,
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
        """Carrera 13 sola = última: no exige EXA; IMP < 12 es aviso."""
        datos = _datos((13, 11, [("IMP", 5000), ("TER", None)]))
        _, violaciones = _validar_carreras_tela(datos)[13]
        assert not any(v[0] == "EXA debería estar" for v in violaciones)
        assert not any(v[0] == "IMP no debería estar" for v in violaciones)
        avisos = [v for v in violaciones if v[2] == "aviso"]
        assert any("IMP" in v[0] and "última" in v[0] for v in avisos)
        assert all(v[2] == "aviso" for v in avisos)

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
        assert any(
            v == ("TER debería estar", "≥ 8 caballos → TER obligatorio", "error")
            for v in violaciones
        )

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


    def test_ultima_carrera_imp_cua_aviso_sin_exa(self):
        items = [
            (n, 10, [("EXA", 2000), ("GAN", None), ("TER", None)])
            for n in range(1, 14)
        ]
        items.append((14, 9, [("IMP", 2000), ("CUA", 1000), ("GAN", None), ("TER", None)]))
        datos = _datos(*items)
        ok, errores, avisos = resumen_validaciones_tela(datos)
        assert ok is True
        assert errores == []
        assert any("IMP" in a and "CUA" in a and "última" in a for a in avisos)
        assert not any("EXA debería estar" in a for a in avisos)
        assert not any("IMP no debería estar" in a for a in avisos)
        html = _html_panel_validaciones(_validar_carreras_tela(datos))
        assert 'class="info"' in html
        assert "IMP y CUA permitidos" in html

    def test_carrera_intermedia_imp_sigue_error(self):
        datos = _datos(
            (6, 9, [("IMP", 2000), ("TER", None)]),
            (7, 10, [("EXA", 2000), ("TER", None)]),
        )
        _, violaciones = _validar_carreras_tela(datos)[6]
        assert any(v[0] == "IMP no debería estar" and v[2] == "error" for v in violaciones)
        assert any(v[0] == "EXA debería estar" and v[2] == "error" for v in violaciones)
        ok, errores, _avisos = resumen_validaciones_tela(datos)
        assert ok is False
        assert any("Carrera 6" in m and "IMP no debería estar" in m for m in errores)


class TestResumenValidacionesComparacion:
    """En comparación SI se validan reglas de tela sobre el oficial, sin EXA/TRI extra."""

    def test_ok_cuando_cumple_reglas(self):
        datos = _datos((1, 10, [("EXA", 2000), ("GAN", None), ("TER", None)]))
        ok, errores, avisos = resumen_validaciones_tela(datos)
        assert ok is True
        assert errores == []
        assert avisos == []

    def test_ignora_exa_tri_extra_no_estan_en_oficial(self):
        """C4 ≥12 con IMP+CUA en tela: EXA/TRI del reporte no deben generar error."""
        oficial = _datos((
            4, 13,
            [("GAN", None), ("TER", None), ("IMP", 2000), ("DOB", 2000), ("CUA", 1000)],
        ))
        ok, errores, _avisos = resumen_validaciones_tela(oficial)
        assert ok is True
        assert not any("EXA" in m or "TRI" in m for m in errores)

    def test_ter_faltante_en_8_caballos(self):
        datos = _datos((1, 8, [("GAN", None), ("EXA", 2000)]))
        ok, errores, _avisos = resumen_validaciones_tela(datos)
        assert ok is False
        assert any("Carrera 1" in m and "TER debería estar" in m for m in errores)

    def test_tri_cua_en_oficial_sigue_siendo_error(self):
        datos = _datos((6, 11, [("EXA", 2000), ("TRI", 2000), ("CUA", 1000), ("TER", None)]))
        ok, errores, _avisos = resumen_validaciones_tela(datos)
        assert ok is False
        assert any(MSG_TRI_CUA_JUNTOS in m for m in errores)

    def test_html_buffer_no_registra_validaciones(self):
        datos = _datos((1, 10, [("EXA", 2000), ("GAN", None), ("TER", None)]))
        buf: list = []
        errores = mostrar_resumen_validaciones_tela(datos, html_buffer=buf)
        assert errores == []
        assert buf == []

    def test_html_comparacion_omite_seccion_validaciones(self, tmp_path):
        from controlcomparador.ui.tables import exportar_comparacion_html

        salida = tmp_path / "cmp.html"
        exportar_comparacion_html(
            [{"titulo": "COMPARACION", "columnas": ["Carr."], "filas": [["1"]]}],
            salida,
            diferencias=[
                ("VALIDACIONES", ["Carrera 1: IMP no debería estar"]),
                ("OFICIAL vs REPORTE", ["Carrera 6: IMP está de más en el reporte"]),
            ],
        )
        html = salida.read_text(encoding="utf-8")
        assert "VALIDACIONES" not in html
        assert "OFICIAL vs REPORTE" in html
        assert "IMP está de más" in html

    def test_reporte_7_caballos_con_ter_falla(self):
        oficial = _datos((10, 8, [("GAN", None), ("TER", None), ("EXA", 2000)]))
        reporte = {
            10: {
                "caballos": 7,
                "apuestas": {"GAN": None, "TER": None, "EXA": None},
            },
        }
        ok, errores, _avisos = resumen_validaciones_tela(oficial, datos_reporte=reporte)
        assert ok is False
        assert any("reporte" in m and "TER no debería estar" in m for m in errores)
        assert not any("oficial" in m and "TER no debería estar" in m for m in errores)

    def test_oficial_sin_ter_sigue_fallando_con_reporte_ok(self):
        oficial = _datos((1, 8, [("GAN", None), ("EXA", 2000)]))
        reporte = {
            1: {"caballos": 8, "apuestas": {"GAN": None, "TER": None, "EXA": None}},
        }
        ok, errores, _avisos = resumen_validaciones_tela(oficial, datos_reporte=reporte)
        assert ok is False
        assert any("oficial" in m and "TER debería estar" in m for m in errores)
