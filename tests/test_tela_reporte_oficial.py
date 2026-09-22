# -*- coding: utf-8 -*-
"""Tela dual: Programa Depurado (vieja) + REPORTE PROGRAMA OFICIAL (nueva)."""

from pathlib import Path

import pytest

from controlcomparador.parsers.pdf import (
    es_apuesta_excluida,
    es_tela_depurada,
    es_tela_oficial,
    es_tela_reporte_oficial,
    tipo_tela_oficial,
    obtener_apuestas_por_carrera,
    normalizar_desde_lista_apuestas,
    extraer_pases_tela_oficial,
    extraer_info_reunion_tela,
    abreviar_apuesta,
    normalizar_nombre_apuesta,
    _contar_caballos_desde_items,
    _contar_caballos_tela_reporte,
    _normalizar_pase,
    _parsear_info_reunion_tela,
    _parsear_linea_bet_reporte,
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
        assert es_tela_depurada(FIXTURE_REPORTE) is False
        assert es_tela_oficial(FIXTURE_REPORTE) is True
        assert tipo_tela_oficial(FIXTURE_REPORTE) == "TELA PROGRAMA OFICIAL"

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
        """Conteo exacto reunión viernes (columna CABALLO + huérfanos pypdf)."""
        esperado = {
            1: 11, 2: 10, 3: 11, 4: 8, 5: 8, 6: 8, 7: 8,
            8: 7, 9: 8, 10: 7, 11: 6, 12: 14, 13: 10, 14: 13,
        }
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(FIXTURE_REPORTE))
        actual = {n: d["caballos"] for n, d in datos.items()}
        assert actual == esperado

    def test_c8_siete_y_c10_siete_sin_sobreconteo(self):
        """Columna CABALLO: C8=7, C10=7 (huérfano 07); sin robar C9."""
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


class TestColumnaCaballoPosicional:
    """Conteo por coordenadas de la columna CABALLO (sin PDF)."""

    def test_sintetico_siete_caballos(self):
        # page, y, x, texto — carrera 8a + CABALLO 01..07 hasta SUPLENTES
        items = [
            (0, 700.0, 30.0, "8"),
            (0, 700.0, 40.0, "a"),
            (0, 650.0, 80.0, "Condición:"),
            (0, 640.0, 90.0, "1000 mts"),
            (0, 600.0, 170.0, "CABALLO"),
            (0, 580.0, 170.0, "01"),
            (0, 560.0, 170.0, "02"),
            (0, 540.0, 170.0, "03"),
            (0, 520.0, 170.0, "04"),
            (0, 500.0, 170.0, "05"),
            (0, 480.0, 170.0, "06"),
            (0, 460.0, 170.0, "07"),
            (0, 420.0, 275.0, "SUPLENTES"),
            (0, 400.0, 170.0, "08"),  # suplente, no cuenta
        ]
        assert _contar_caballos_desde_items(items) == {8: 7}

    def test_carrera_15_detectada_y_cuenta_caballos(self):
        """Reuniones con C15: el nro ya no está limitado a 1–14 (tope 1–22)."""
        items = [
            (0, 800.0, 30.0, "14"),
            (0, 800.0, 42.0, "a"),
            (0, 780.0, 80.0, "Condición:"),
            (0, 700.0, 170.0, "CABALLO"),
            (0, 680.0, 170.0, "01"),
            (0, 660.0, 170.0, "02"),
            (0, 640.0, 170.0, "03"),
            (0, 620.0, 170.0, "04"),
            (0, 600.0, 170.0, "05"),
            (0, 580.0, 170.0, "06"),
            (0, 560.0, 170.0, "07"),
            (0, 540.0, 170.0, "08"),
            (0, 520.0, 170.0, "09"),
            (0, 500.0, 170.0, "10"),
            (0, 450.0, 275.0, "SUPLENTES"),
            (1, 800.0, 30.0, "15"),
            (1, 800.0, 42.0, "a"),
            (1, 780.0, 80.0, "Condición:"),
            (1, 700.0, 170.0, "CABALLO"),
            (1, 680.0, 170.0, "01"),
            (1, 660.0, 170.0, "02"),
            (1, 640.0, 170.0, "03"),
            (1, 620.0, 170.0, "04"),
            (1, 600.0, 170.0, "05"),
            (1, 580.0, 170.0, "06"),
            (1, 560.0, 170.0, "07"),
            (1, 540.0, 170.0, "08"),
            (1, 520.0, 170.0, "09"),
            (1, 500.0, 170.0, "10"),
            (1, 480.0, 170.0, "11"),
            (1, 460.0, 170.0, "12"),
            (1, 400.0, 275.0, "SUPLENTES"),
        ]
        out = _contar_caballos_desde_items(items)
        assert out[14] == 10
        assert out[15] == 12

    def test_columna_sparse_c4_une_orphans(self):
        """Solo 09 en columna + orphans 01–08,10 → 10 (no caer a segmento)."""
        items = [
            (0, 800.0, 30.0, "4"),
            (0, 800.0, 42.0, "a"),
            (0, 780.0, 80.0, "Condición:"),
            (0, 700.0, 170.0, "CABALLO"),
            (0, 400.0, 170.0, "09"),
            (0, 300.0, 275.0, "SUPLENTES"),
            (0, 900.0, 0.0, "01"),
            (0, 900.0, 0.0, "02"),
            (0, 900.0, 0.0, "03"),
            (0, 900.0, 0.0, "04"),
            (0, 900.0, 0.0, "05"),
            (0, 900.0, 0.0, "06"),
            (0, 900.0, 0.0, "07"),
            (0, 900.0, 0.0, "08"),
            (0, 900.0, 0.0, "10"),
        ]
        assert _contar_caballos_desde_items(items)[4] == 10

    def test_columna_sparse_c6_une_orphans(self):
        """Columna {03,04} + orphans → 8."""
        items = [
            (0, 800.0, 30.0, "6"),
            (0, 800.0, 42.0, "a"),
            (0, 780.0, 80.0, "Condición:"),
            (0, 700.0, 170.0, "CABALLO"),
            (0, 620.0, 170.0, "03"),
            (0, 580.0, 170.0, "04"),
            (0, 350.0, 275.0, "SUPLENTES"),
            (0, 900.0, 0.0, "01"),
            (0, 900.0, 0.0, "02"),
            (0, 900.0, 0.0, "05"),
            (0, 900.0, 0.0, "06"),
            (0, 900.0, 0.0, "07"),
            (0, 900.0, 0.0, "08"),
        ]
        assert _contar_caballos_desde_items(items)[6] == 8

    def test_carrera_22_detectada(self):
        """Tope superior del detector: carrera 22."""
        items = [
            (0, 800.0, 30.0, "22"),
            (0, 800.0, 42.0, "a"),
            (0, 780.0, 80.0, "Condición:"),
            (0, 700.0, 170.0, "CABALLO"),
            (0, 680.0, 170.0, "01"),
            (0, 660.0, 170.0, "02"),
            (0, 640.0, 170.0, "03"),
            (0, 620.0, 170.0, "04"),
            (0, 600.0, 170.0, "05"),
            (0, 550.0, 275.0, "SUPLENTES"),
        ]
        assert _contar_caballos_desde_items(items)[22] == 5

    def test_huerfanos_completan_agujeros_c2(self):
        """Dorsales parciales + huérfanos x≈0 → 10 (no 11 del fallback frágil)."""
        items = [
            (0, 800.0, 30.0, "2"),
            (0, 800.0, 40.0, "a"),
            (0, 750.0, 80.0, "Condición:"),
            (0, 700.0, 170.0, "CABALLO"),
            (0, 620.0, 170.0, "04"),
            (0, 560.0, 170.0, "06"),
            (0, 530.0, 170.0, "07"),
            (0, 400.0, 275.0, "SUPLENTES"),
            # huérfanos pypdf (matriz rota)
            (0, 900.0, 0.0, "01"),
            (0, 900.0, 0.0, "02"),
            (0, 900.0, 0.0, "03"),
            (0, 900.0, 0.0, "05"),
            (0, 900.0, 0.0, "08"),
            (0, 900.0, 0.0, "09"),
            (0, 900.0, 0.0, "10"),
        ]
        assert _contar_caballos_desde_items(items)[2] == 10

    def test_huerfano_extiende_por_hueco_a_suplentes(self):
        """01–06 contiguos + hueco a SUPLENTES + huérfano 07 → 7."""
        items = [
            (0, 500.0, 30.0, "10"),
            (0, 500.0, 45.0, "a"),
            (0, 450.0, 80.0, "Condición:"),
            (0, 400.0, 170.0, "CABALLO"),
            (0, 380.0, 170.0, "01"),
            (0, 350.0, 170.0, "02"),
            (0, 320.0, 170.0, "03"),
            (0, 290.0, 170.0, "04"),
            (0, 260.0, 170.0, "05"),
            (0, 230.0, 170.0, "06"),
            (0, 170.0, 275.0, "SUPLENTES"),  # room ~60 vs gap~30
            (0, 900.0, 0.0, "07"),
        ]
        assert _contar_caballos_desde_items(items)[10] == 7

    def test_multipagina_une_continuacion(self):
        items = [
            (0, 400.0, 30.0, "4"),
            (0, 400.0, 40.0, "a"),
            (0, 350.0, 80.0, "Condición:"),
            (0, 300.0, 170.0, "CABALLO"),
            (0, 280.0, 170.0, "01"),
            (0, 260.0, 170.0, "02"),
            (0, 240.0, 170.0, "03"),
            (0, 220.0, 170.0, "04"),
            (0, 200.0, 170.0, "05"),
            (0, 180.0, 170.0, "06"),
            (0, 160.0, 170.0, "07"),
            (1, 800.0, 170.0, "CABALLO"),
            (1, 780.0, 170.0, "08"),
            (1, 750.0, 275.0, "SUPLENTES"),
            (1, 500.0, 30.0, "5"),
            (1, 500.0, 40.0, "a"),
            (1, 450.0, 80.0, "Condición:"),
        ]
        assert _contar_caballos_desde_items(items)[4] == 8

    def test_continuacion_no_toma_huerfano_espurio(self):
        """Salto de página: 01–08 incompletos + 09; huérfano 10 en p1 no cuenta."""
        items = [
            (0, 500.0, 30.0, "10"),
            (0, 500.0, 45.0, "a"),
            (0, 450.0, 80.0, "Condición:"),
            (0, 400.0, 170.0, "CABALLO"),
            (0, 380.0, 170.0, "01"),
            (0, 320.0, 170.0, "04"),
            (0, 290.0, 170.0, "05"),
            (0, 230.0, 170.0, "07"),
            (0, 200.0, 170.0, "08"),
            # huérfanos correctos en página principal
            (0, 900.0, 0.0, "02"),
            (0, 900.0, 0.0, "03"),
            (0, 900.0, 0.0, "06"),
            # continuación
            (1, 800.0, 170.0, "CABALLO"),
            (1, 780.0, 170.0, "09"),
            (1, 740.0, 275.0, "SUPLENTES"),
            # ruido de página siguiente (no debe subir a 10)
            (1, 900.0, 0.0, "10"),
            (1, 900.0, 0.0, "01"),
            (1, 900.0, 0.0, "03"),
        ]
        assert _contar_caballos_desde_items(items)[10] == 9

    def test_infiere_columna_sin_header_caballo(self):
        """C1 jueves: header CABALLO en x≈0; dorsales en banda + huérfanos → 10."""
        items = [
            (0, 570.0, 30.0, "1"),
            (0, 570.0, 40.0, "a"),
            (0, 520.0, 80.0, "Condición:"),
            # header inutilizable
            (0, 800.0, 0.0, "CABALLO"),
            (0, 420.0, 157.0, "01"),
            (0, 380.0, 157.0, "02"),
            (0, 320.0, 157.0, "04"),
            (0, 180.0, 157.0, "09"),
            (0, 120.0, 275.0, "SUPLENTES"),
            (0, 900.0, 0.0, "03"),
            (0, 900.0, 0.0, "05"),
            (0, 900.0, 0.0, "06"),
            (0, 900.0, 0.0, "07"),
            (0, 900.0, 0.0, "08"),
            (0, 900.0, 0.0, "10"),
            # C2 al pie (hs) para no robar grilla ajena
            (0, 50.0, 30.0, "2"),
            (0, 50.0, 40.0, "a"),
            (0, 30.0, 20.0, "14:25 hs"),
            (1, 800.0, 80.0, "Condición:"),
            (1, 700.0, 170.0, "CABALLO"),
            (1, 680.0, 170.0, "01"),
            (1, 660.0, 170.0, "02"),
            (1, 640.0, 170.0, "03"),
            (1, 620.0, 170.0, "04"),
            (1, 600.0, 170.0, "05"),
            (1, 580.0, 170.0, "06"),
            (1, 560.0, 275.0, "SUPLENTES"),
        ]
        out = _contar_caballos_desde_items(items)
        assert out[1] == 10
        assert out[2] == 6

    def test_suplentes_debajo_no_cuentan(self):
        """Dorsales bajo SUPLENTES no entran al conteo."""
        items = [
            (0, 700.0, 30.0, "3"),
            (0, 700.0, 40.0, "a"),
            (0, 650.0, 80.0, "Condición:"),
            (0, 600.0, 170.0, "CABALLO"),
            (0, 580.0, 170.0, "01"),
            (0, 560.0, 170.0, "02"),
            (0, 540.0, 170.0, "03"),
            (0, 520.0, 170.0, "04"),
            (0, 500.0, 170.0, "05"),
            (0, 480.0, 275.0, "SUPLENTES"),
            (0, 460.0, 170.0, "06"),
            (0, 440.0, 170.0, "07"),
        ]
        assert _contar_caballos_desde_items(items)[3] == 5


_DOWNLOADS = Path(r"C:/Users/cdiaz/Downloads")
PDF_MIERCOLES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL MIERCOLES*.pdf"), None)
PDF_VIERNES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL VIERNES*.pdf"), None)
PDF_JUEVES = next(_DOWNLOADS.glob("REPORTE PROGRAMA OFICIAL JUEVES*.pdf"), None)
PDF_SABADO_26 = next(
    _DOWNLOADS.glob("Programa Oficial Sabado 26 de septiembre*.pdf"), None
)


@pytest.mark.skipif(PDF_SABADO_26 is None, reason="PDF sábado 26/09 no disponible")
class TestTelaReporteSabado26:
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


class TestContarCaballosTrasApuestas:
    """pypdf suele poner dorsales después de APUESTAS y antes de STUD."""

    def test_lista_tras_apuestas_cuenta_caballos(self):
        race_lines = [
            "2a PREMIO EJEMPLO 2026",
            "APUESTAS",
            "Exacta $2.000",
            "01 CABALLO UNO",
            "02 CABALLO DOS",
            "03 CABALLO TRES",
            "04 CABALLO CUATRO",
            "05 CABALLO CINCO",
            "06 CABALLO SEIS",
            "07 CABALLO SIETE",
            "08 CABALLO OCHO",
            "09 CABALLO NUEVE",
            "10 CABALLO DIEZ",
            "STUD 4 ÚLTIMAS",
        ]
        cab, pending, consumio = _contar_caballos_tela_reporte([], race_lines, None)
        assert cab == 10
        assert pending is None
        assert consumio is False

    def test_lista_en_segmento_pisa_pending_incompleto(self):
        race_lines = [
            "9a PREMIO OTRO 2026",
            "APUESTAS",
            "01 ALPHA",
            "02 BETA",
            "03 GAMMA",
            "04 DELTA",
            "05 EPSILON",
            "06 ZETA",
            "07 ETA",
            "STUD X",
        ]
        cab, _, consumio = _contar_caballos_tela_reporte([], race_lines, {1, 2})
        assert cab == 7
        assert consumio is False

    def test_no_roba_unica_secuencia_de_carrera_anterior(self):
        prev = [
            "7a PREMIO ANT 2026",
            "01 A",
            "02 B",
            "03 C",
            "04 D",
            "05 E",
            "06 F",
            "07 G",
        ]
        race = ["8a PREMIO VACIA 2026", "APUESTAS", "Exacta $2.000", "STUD 4"]
        cab, _, consumio = _contar_caballos_tela_reporte(prev, race, None)
        assert cab == 0
        assert consumio is False

    def test_lookahead_dorsales_en_siguiente_carrera(self):
        race = ["8a PREMIO VACIA 2026", "APUESTAS", "Exacta $2.000", "STUD 4"]
        nxt = [
            "9a PREMIO SIG 2026",
            "APUESTAS",
            "01 A", "02 B", "03 C", "04 D", "05 E",
            "01 F", "02 G", "03 H", "04 I", "05 J", "06 K", "07 L",
        ]
        cab, _, consumio = _contar_caballos_tela_reporte([], race, None, next_lines=nxt)
        assert cab == 5
        assert consumio is True
        cab9, _, _ = _contar_caballos_tela_reporte(
            [], nxt, None, skip_first_seq=True
        )
        assert cab9 == 7

    def test_stud_nombre_no_parte_secuencia(self):
        from controlcomparador.parsers.pdf import _secuencias_dorsales

        lineas = [
            "01 UNAFRAID",
            "02 SCRATCH",
            "03 MESSIAS",
            "04 MARCANDO",
            "05 BOBBY",
            "06 GO DANCING",
            "07 LARGE DREAM",
            "STUD GRR (CDIA)2SI-1SI 08 IN MATIC BLANCO",
            "SUPLENTES",
            "01 RICHARD",
            "02 MUST NOT",
            "STUD ALDEA STA",
            "03 LEGOLANDS",
            "04 HIT",
            "05 CHACO",
            "06 CHIMENTOS",
            "07 HARLAN'S",
            "08 HABLA DE",
            "STUD 4 ÚLTIMASCABALLO JOCKEY ENTRENADOR",
        ]
        seqs = _secuencias_dorsales(lineas)
        assert sorted(seqs[0]) == list(range(1, 9))
        assert sorted(seqs[1]) == list(range(1, 9))

    def test_pending_completo_no_pisado_por_in_race_corto(self):
        race = [
            "7a PREMIO X 2026",
            "APUESTAS",
            "01 VIEJO",
            "02 SILVER",
            "03 SANTO",
            "04 PLAYA",
            "05 BLUE",
            "06 CAPRICHO",
            "07 HI DOLFI",
            "STUD 4 ÚLTIMAS",
        ]
        pending = set(range(1, 9))
        cab, next_pend, consumio = _contar_caballos_tela_reporte(
            [], race, pending
        )
        assert cab == 8
        assert consumio is False
        # Bloque 01-07 descartado pasa a la siguiente (C8)
        assert next_pend is not None and max(next_pend) == 7

    def test_lookahead_no_roba_si_segunda_es_suplente(self):
        """C8 vacío no debe tomar 01-08 de C9 si el 2º bloque es suplente más corto."""
        race = ["8a CLASICO VACIA 2026", "APUESTAS", "STUD 4 ÚLTIMAS"]
        nxt = [
            "9a PREMIO SIG 2026",
            "APUESTAS",
            "01 A", "02 B", "03 C", "04 D", "05 E", "06 F", "07 G", "08 H",
            "SUPLENTES",
            "01 S1", "02 S2", "03 S3", "04 S4", "05 S5", "06 S6", "07 S7",
        ]
        cab, _, consumio = _contar_caballos_tela_reporte(
            [], race, None, next_lines=nxt
        )
        assert cab == 0
        assert consumio is False

    def test_no_hereda_prev_si_tiene_dorsales_propios(self):
        """C10 con 01-06 no debe heredar los 8 de C9 vía seqs_prev[-2]."""
        prev = [
            "9a PREMIO 2026",
            "01 A", "02 B", "03 C", "04 D", "05 E", "06 F", "07 G", "08 H",
            "SUPLENTES",
            "01 S", "02 S", "03 S", "04 S", "05 S", "06 S", "07 S",
        ]
        race = [
            "10a PREMIO 2026",
            "APUESTAS",
            "01 TREN",
            "02 SECRETO",
            "03 NUESTRO",
            "04 MATUTE",
            "05 BELLO",
            "06 MARTINIQUE",
            "STUD 4 ÚLTIMAS",
        ]
        cab, _, _ = _contar_caballos_tela_reporte(prev, race, None)
        assert cab == 6

    def test_orphan_in_race_pasa_a_siguiente_vacia(self):
        """Pending 8 + in_race 01-07 → C7=8 y C8 vacía recibe 7."""
        race7 = [
            "7a PREMIO 2026",
            "APUESTAS",
            "01 VIEJO",
            "02 SILVER",
            "03 SANTO",
            "04 PLAYA",
            "05 BLUE",
            "06 CAPRICHO",
            "07 HI DOLFI",
            "STUD 4 ÚLTIMAS",
        ]
        race8 = ["8a CLASICO 2026", "APUESTAS", "STUD 4 ÚLTIMAS"]
        cab7, pend, _ = _contar_caballos_tela_reporte(
            [], race7, set(range(1, 9))
        )
        assert cab7 == 8
        assert pend is not None and max(pend) == 7
        cab8, _, consumio = _contar_caballos_tela_reporte(
            [], race8, pend, next_lines=None
        )
        assert cab8 == 7
        assert consumio is False

    def test_lookahead_no_si_hay_pending(self):
        race = ["8a PREMIO VACIA 2026", "APUESTAS", "Exacta $2.000", "STUD 4"]
        nxt = [
            "9a PREMIO SIG 2026",
            "01 A", "02 B", "03 C", "04 D", "05 E",
            "01 F", "02 G", "03 H", "04 I", "05 J", "06 K", "07 L", "08 M",
        ]
        cab, _, consumio = _contar_caballos_tela_reporte(
            [], race, set(range(1, 8)), next_lines=nxt
        )
        assert cab == 7
        assert consumio is False

    def test_pending_debil_completa_con_continuacion_siguiente(self):
        """C2 vacía: suplentes 01-03 en C1 + 04-11 al inicio de C3."""
        race = ["2a PREMIO VACIA 2026", "APUESTAS", "STUD 4 ÚLTIMAS"]
        nxt = [
            "3a PREMIO SIG 2026",
            "04 DEPECHE",
            "05 BARBA",
            "06 BEAUTIFUL",
            "07 DE",
            "08 CATALINO",
            "09 CASTA",
            "10 VACATION",
            "11 PUERTO",
            "01 OTRO",
            "02 MAS",
            "03 TRES",
            "04 CUATRO",
            "05 CINCO",
            "06 SEIS",
            "07 SIETE",
        ]
        cab, _, consumio = _contar_caballos_tela_reporte(
            [], race, {1, 2, 3}, next_lines=nxt
        )
        assert cab == 11
        assert consumio is False

    def test_no_roba_lista_siguiente_si_prev_tiene_caballos(self):
        """C1 con dorsales en prev no debe consumir el bloque 01..10 de C2."""
        prev = [
            "01 TIMBRADO",
            "02 TIGRE",
            "03 SUENO",
            "04 ROMBO",
            "05 ACTIUS",
            "06 IL FACCIA",
            "07 RICHARLISON",
            "08 LOVELY",
            "09 JAZZ",
        ]
        race1 = ["1a PREMIO HURACAN 2025", "APUESTAS", "STUD 4 ÚLTIMAS"]
        race2 = [
            "2a PREMIO NASHVILLE 2015",
            "APUESTAS",
            "01 POTRI SI",
            "02 INCAICO",
            "03 GIVE ME",
            "04 FLITZER",
            "05 BINCAAL",
            "06 ECOS",
            "07 FADE",
            "08 ES MANCHESTER",
            "09 EL INDOLENTE",
            "10 ULTRA PLUS",
            "SUPLENTES",
            "01 WINNING",
            "02 THE GUARDIAN",
            "03 SABIN",
            "04 MONTREAL",
            "05 CRAMBERRY",
        ]
        cab1, _, cons1 = _contar_caballos_tela_reporte(
            prev, race1, None, race2, False, prev_preheader=True
        )
        assert cab1 == 9
        assert cons1 is False
        cab2, _, cons2 = _contar_caballos_tela_reporte([], race2, None, None, cons1)
        assert cab2 == 10
        assert cons2 is False
