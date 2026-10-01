# -*- coding: utf-8 -*-
"""REPORTE PROGRAMA OFICIAL San Isidro."""

from pathlib import Path

import pytest

from controlcomparador.parsers.pdf import (
    es_apuesta_excluida,
    es_tela_oficial,
    es_tela_reporte_oficial,
    tipo_tela_oficial,
    obtener_apuestas_por_carrera,
    normalizar_desde_lista_apuestas,
    extraer_pases_tela_oficial,
    extraer_info_reunion_tela,
    abreviar_apuesta,
    normalizar_nombre_apuesta,
    _normalizar_pase,
    _parsear_info_reunion_tela,
    _parsear_linea_bet_reporte,
    _parsear_bets_en_linea_reporte,
)
from controlcomparador.ui import tables

FIXTURE_REPORTE = Path(__file__).parent / "fixtures" / "tela_reporte_programa_oficial_si.pdf"


class TestExclusionPasesGrado:
    @pytest.mark.parametrize(
        "nombre,debe_excluir",
        [
            ("Doble $2000", False),
            ("Doble 1° Pase $2000", False),
            ("Doble 1º Pase $2000", False),
            ("Doble 1\ufffd Pase $2000", False),
            ("Doble último pase", True),
            ("Doble 2° Pase", True),
            ("Cuaterna 1° Pase $2000", False),
            ("Cuaterna 2° Pase", True),
            ("Cuaterna (Final) 1° Pase$2000", False),
            ("Quintuplo 1° Pase$1000", False),
        ],
    )
    def test_doble_y_grado(self, nombre, debe_excluir):
        assert es_apuesta_excluida(nombre) is debe_excluir


class TestNormalizarPaseGrado:
    def test_grado_a_er(self):
        assert _normalizar_pase("1° Pase") == "1er.Pase"
        assert _normalizar_pase("2º Pase") == "2do.Pase"
        assert _normalizar_pase("3\ufffd Pase") == "3er.Pase"
        assert _normalizar_pase("último pase") == "Ultimo Pase"


class TestInfoReunionReporte:
    def test_parsea_reunion_fecha_hipodromo(self):
        texto = (
            "HIPÓDROMO DE SAN ISIDROPROGRAMA OFICIAL"
            "Reunión N° 85 - viernes 18 de septiembre de 2026\n"
            "TOTAL EN POZOS $1\n"
        )
        info = _parsear_info_reunion_tela(texto)
        assert info["reunion"] == "85"
        assert info["fecha"] == "18/09/2026"
        assert "San Isidro" in info["hipodromo"]


@pytest.mark.skipif(not FIXTURE_REPORTE.exists(), reason="fixture PDF ausente")
class TestTelaReporteProgramaOficial:
    def test_deteccion(self):
        assert es_tela_reporte_oficial(FIXTURE_REPORTE) is True
        assert es_tela_oficial(FIXTURE_REPORTE) is True
        assert tipo_tela_oficial(FIXTURE_REPORTE) == "PROGRAMA OFICIAL"

    def test_info_reunion(self):
        info = extraer_info_reunion_tela(FIXTURE_REPORTE)
        assert info["reunion"] == "85"
        assert info["fecha"] == "18/09/2026"

    def test_bases_carrera_1(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert 1 in datos
        ap = datos[1]["apuestas"]
        assert ap.get("EXA") == 2000.0
        assert ap.get("TRI") == 2000.0
        assert ap.get("DOB") == 2000.0
        assert ap.get("QTN") == 2000.0

    def test_carrera_2_cadena_y_pases(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert datos[2]["apuestas"].get("CAD") == 500.0
        pases = extraer_pases_tela_oficial(FIXTURE_REPORTE)
        assert "1er.Pase" in pases[2].get("CAD", set())
        assert "Ultimo Pase" in pases[2].get("DOB", set())

    def test_carrera_8_clasico(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert 8 in datos
        assert datos[8]["apuestas"].get("QTP") == 1000.0

    def test_carrera_12_imp_cua(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert datos[12]["apuestas"].get("IMP") == 2000.0
        assert datos[12]["apuestas"].get("CUA") == 2000.0

    def test_carrera_14_tiene_imp(self):
        """C14 debe incluir IMP (en fixture es Imperfecta $2.000)."""
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert datos[14]["apuestas"].get("IMP") == 2000.0
        assert datos[14]["apuestas"].get("CUA") == 2000.0

    def test_smoke_resumen_sin_crash(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        pases = extraer_pases_tela_oficial(FIXTURE_REPORTE)
        for n, p in pases.items():
            if n in datos:
                datos[n]["pases"] = p
        tables.imprimir_resumen_tela(datos, str(FIXTURE_REPORTE))

    def test_ninguna_carrera_con_cero_caballos(self):
        """Regresión: C2/C9 del miércoles 23/9 daban caballos=0 (lista tras APUESTAS)."""
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        sin_caballos = [n for n, d in datos.items() if d.get("caballos", 0) <= 0]
        assert sin_caballos == [], f"carreras sin caballos: {sin_caballos}"

    def test_c7_y_c9_ocho_caballos(self):
        """Regresión: STUD nombre partía listas; C7/C9 quedaban en 7 y TER en falso."""
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert datos[7]["caballos"] == 8
        assert datos[9]["caballos"] == 8
        assert datos[2]["caballos"] == 10

    def test_mapa_caballos_viernes_esperado(self):
        """Conteo exacto reunión viernes (dos carreras por hoja, bloques CHAQUETILLAS)."""
        esperado = {
            1: 11, 2: 10, 3: 11, 4: 8, 5: 8, 6: 8, 7: 8,
            8: 7, 9: 8, 10: 7, 11: 6, 12: 14, 13: 10, 14: 13,
        }
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        actual = {n: d["caballos"] for n, d in datos.items()}
        assert actual == esperado

    def test_c8_siete_y_c10_siete_sin_sobreconteo(self):
        """C8=7, C10=7; sin robar C9."""
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        assert datos[8]["caballos"] == 7
        assert datos[10]["caballos"] == 7
        assert datos[9]["caballos"] == 8
        assert datos[11]["caballos"] > 0

    def test_sin_ter_falso_en_c8_c10(self):
        """C8=7 y C10=7 no deben exigir TER (≥8)."""
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        vals = tables._validar_carreras_tela(datos)
        ter_c8_c10 = []
        for nro in (8, 10):
            _cab, hallazgos = vals.get(nro, (0, []))
            for h in hallazgos:
                if "TER" in str(h):
                    ter_c8_c10.append((nro, h))
        assert ter_c8_c10 == [], f"falsos TER: {ter_c8_c10}"


class TestImperfectaExtraParseo:
    @pytest.mark.parametrize(
        "linea,valor",
        [
            ("Imperfecta(Extra) $5.000", "5.000"),
            ("Imperfecta (Extra) $5.000", "5.000"),
            ("Imperfecta extra $5.000", "5.000"),
            ("Imperfecta $2.000", "2.000"),
        ],
    )
    def test_parsea_y_abrevia_a_imp(self, linea, valor):
        parsed = _parsear_linea_bet_reporte(linea)
        assert parsed is not None
        nombre, val = parsed
        assert val == valor
        assert abreviar_apuesta(normalizar_nombre_apuesta(nombre)) == "IMP"


class TestBetsMultilineaExport8248:
    """Export numérico pega varias apuestas en una sola línea de texto."""

    def test_tercero_y_exacta_en_misma_linea(self):
        bets = _parsear_bets_en_linea_reporte("Tercero $2  Exacta $2.000")
        codigos = [
            abreviar_apuesta(normalizar_nombre_apuesta(n)) for n, _v in bets
        ]
        assert codigos == ["TER", "EXA"]
        assert bets[1][1] == "2.000"

    def test_ganador_y_segundo_en_misma_linea(self):
        bets = _parsear_bets_en_linea_reporte("Ganador $2 Segundo $2")
        codigos = [
            abreviar_apuesta(normalizar_nombre_apuesta(n)) for n, _v in bets
        ]
        assert codigos == ["GAN", "SEG"]

    def test_cuaterna_y_cadena_en_misma_linea(self):
        bets = _parsear_bets_en_linea_reporte(
            "Cuaterna 2° Pase Cadena 1° Pase $500"
        )
        assert len(bets) == 2
        n0, v0 = bets[0]
        n1, v1 = bets[1]
        assert abreviar_apuesta(normalizar_nombre_apuesta(n0)) == "QTN"
        assert es_apuesta_excluida(n0)  # 2° Pase
        assert abreviar_apuesta(normalizar_nombre_apuesta(n1)) == "CAD"
        assert not es_apuesta_excluida(n1)
        assert v1 == "500"

    def test_linea_simple_sigue_una_sola(self):
        bets = _parsear_bets_en_linea_reporte("Exacta $2.000")
        assert len(bets) == 1
        assert abreviar_apuesta(normalizar_nombre_apuesta(bets[0][0])) == "EXA"


_DOWNLOADS = Path(r"C:/Users/cdiaz/Downloads")
PDF_MIERCOLES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL MIERCOLES*.pdf"), None)
PDF_VIERNES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL VIERNES*.pdf"), None)
PDF_JUEVES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL JUEVES*.pdf"), None)
PDF_SABADO_26 = next(
    _DOWNLOADS.glob("Programa Oficial Sabado 26 de septiembre*.pdf"), None
)
PDF_8248 = next(_DOWNLOADS.glob("2026-09-22_8248.pdf"), None)


@pytest.mark.skipif(PDF_SABADO_26 is None, reason="PDF sábado 26/09 no disponible")
class TestTelaReporteSabado26:
    def test_tipo_es_programa_oficial(self):
        assert tipo_tela_oficial(PDF_SABADO_26) == "PROGRAMA OFICIAL"

    def test_carrera_15_no_queda_en_cero(self):
        """Bug: detector limitaba nros a 1–14 → C15=0 y C14 absorbía caballos."""
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_SABADO_26)
        )
        assert 15 in datos
        assert datos[15]["caballos"] == 12
        assert datos[14]["caballos"] == 10
        assert all(d["caballos"] > 0 for d in datos.values())

    def test_mapa_c4_a_c7_orphans_sparse(self):
        """Columna sparse + orphans: C4=10, C5=9, C6=8, C7=9."""
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_SABADO_26)
        )
        assert datos[4]["caballos"] == 10
        assert datos[5]["caballos"] == 9
        assert datos[6]["caballos"] == 8
        assert datos[7]["caballos"] == 9


@pytest.mark.skipif(PDF_8248 is None, reason="PDF 2026-09-22_8248 no disponible")
class TestTelaExport8248:
    """Export numérico con CABALLO x=0 / dorsales x≈205 — misma reunión 88 que Sabado."""

    def test_tipo_es_programa_oficial(self):
        assert tipo_tela_oficial(PDF_8248) == "PROGRAMA OFICIAL"

    def test_carrera_15_y_c6_alineados(self):
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_8248)
        )
        assert datos[15]["caballos"] == 12
        assert datos[6]["caballos"] == 8
        assert all(d["caballos"] > 0 for d in datos.values())

    def test_mapa_c4_a_c7(self):
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_8248)
        )
        assert datos[4]["caballos"] == 10
        assert datos[5]["caballos"] == 9
        assert datos[6]["caballos"] == 8
        assert datos[7]["caballos"] == 9

    def test_exacta_en_carreras_con_leq_11_caballos(self):
        """Bug: Exacta pegada a Tercero no se leía → 'EXA debería estar'."""
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_8248)
        )
        for n, d in datos.items():
            if d["caballos"] <= 11:
                assert "EXA" in d["apuestas"], f"C{n} sin EXA"
        assert "SEG" in datos[1]["apuestas"]


@pytest.mark.skipif(
    PDF_8248 is None or PDF_SABADO_26 is None,
    reason="Faltan PDF 8248 y/o Sabado 26",
)
class TestTelaAmbosExportsMismaReunion:
    def test_mapa_caballos_igual_entre_exports(self):
        sab = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_SABADO_26)
        )
        num = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_8248)
        )
        mapa_sab = {n: d["caballos"] for n, d in sab.items()}
        mapa_num = {n: d["caballos"] for n, d in num.items()}
        assert mapa_num == mapa_sab
        assert mapa_sab[15] == 12
        assert mapa_sab[6] == 8


@pytest.mark.skipif(PDF_MIERCOLES is None, reason="PDF miércoles no disponible")
class TestTelaReporteMiercoles:
    def test_mapa_caballos_miercoles_esperado(self):
        esperado = {
            1: 9, 2: 10, 3: 8, 4: 10, 5: 9, 6: 10,
            7: 14, 8: 5, 9: 8, 10: 9, 11: 10, 12: 16,
        }
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_MIERCOLES)
        )
        actual = {n: d["caballos"] for n, d in datos.items()}
        assert actual == esperado


@pytest.mark.skipif(PDF_VIERNES is None, reason="PDF viernes no disponible")
class TestTelaReporteViernesDownloads:
    def test_mapa_caballos_viernes_downloads(self):
        esperado = {
            1: 11, 2: 10, 3: 11, 4: 8, 5: 8, 6: 8, 7: 8,
            8: 7, 9: 8, 10: 7, 11: 6, 12: 14, 13: 10, 14: 13,
        }
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_VIERNES)
        )
        assert {n: d["caballos"] for n, d in datos.items()} == esperado

    def test_carrera_14_imperfecta_extra_5000(self):
        """PDF real: Imperfecta(Extra) $5.000 → IMP 5000."""
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_VIERNES)
        )
        assert datos[14]["apuestas"].get("IMP") == 5000.0
        assert datos[12]["apuestas"].get("IMP") == 2000.0


@pytest.mark.skipif(PDF_JUEVES is None, reason="PDF jueves no disponible")
class TestTelaReporteJueves:
    def test_mapa_caballos_jueves_esperado(self):
        """C1=10 (no 6); C2=6 hasta SUPLENTES (no 7 del segmento)."""
        esperado = {
            1: 10, 2: 6, 3: 11, 4: 7, 5: 9, 6: 8, 7: 9,
            8: 9, 9: 8, 10: 6, 11: 6, 12: 14, 13: 16,
        }
        datos = normalizar_desde_lista_apuestas(
            obtener_apuestas_por_carrera(PDF_JUEVES)
        )
        assert {n: d["caballos"] for n, d in datos.items()} == esperado
