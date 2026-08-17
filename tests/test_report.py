from pathlib import Path

from controlcomparador.parsers.report import (
    expandir_race_map,
    normalizar_reporte,
    normalizar_reporte_palermo,
)


class TestExpandirRaceMap:

    def test_all_devuelve_1_a_15(self):
        assert expandir_race_map("ALL") == list(range(1, 16))

    def test_rango_simple(self):
        assert expandir_race_map("1-5") == [1, 2, 3, 4, 5]

    def test_carrera_unica(self):
        assert expandir_race_map("3") == [3]

    def test_lista_separada_por_comas(self):
        assert expandir_race_map("1,3,5") == [1, 3, 5]

    def test_lista_con_rango(self):
        assert expandir_race_map("2,4,6-8") == [2, 4, 6, 7, 8]

    def test_rango_inverso_devuelve_lista_vacia(self):
        assert expandir_race_map("5-3") == []

    def test_string_invalido_devuelve_vacio(self):
        assert expandir_race_map("XYZ") == []

    def test_con_espacios(self):
        assert expandir_race_map(" 1 - 3 ") == [1, 2, 3]

    def test_con_guion_y_coma_mixto(self):
        assert expandir_race_map("1-2,5,7-8") == [1, 2, 5, 7, 8]

    def test_unico_numero_grande(self):
        assert expandir_race_map("12") == [12]


class TestNormalizarReporte:

    def test_parsea_carreras_y_apuestas(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert 1 in resultado
        assert 2 in resultado
        assert "caballos" in resultado[1]
        assert "apuestas" in resultado[1]

    def test_caballo_key_existe(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert "caballos" in resultado[1]

    def test_apuestas_carrera_1_tiene_exa(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert "EXA" in resultado[1]["apuestas"]

    def test_valor_exa_carrera_1(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert resultado[1]["apuestas"]["EXA"] is None
        assert resultado[1]["bases"]["EXA"] == 500.0

    def test_valor_tri_carrera_1(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert resultado[1]["apuestas"]["TRI"] is None
        assert resultado[1]["bases"]["TRI"] == 1200.0

    def test_valor_exa_carrera_2(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert resultado[2]["apuestas"]["EXA"] is None
        assert resultado[2]["bases"]["EXA"] == 550.0

    def test_gan_sin_valor_en_rsm(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert resultado[1]["apuestas"].get("GAN") is None

    def test_seg_sin_valor_en_rsm(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert resultado[1]["apuestas"].get("SEG") is None

    def test_ter_sin_valor_en_rsm(self, ruta_reporte_ejemplo):
        resultado, _ = normalizar_reporte(ruta_reporte_ejemplo)
        assert "TER" in resultado[1]["apuestas"]
        assert resultado[1]["apuestas"]["TER"] is None

    def test_ter_borrado_de_cabecera_no_aparece(self, tmp_path: Path):
        ruta = tmp_path / "card.txt"
        ruta.write_text(
            " 1  GAN       SEG         1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9\n"
            "        EXA       TRI\n"
            "        DOB( 1,2 )\n"
            "        QTN( 1,2,3,4 )\n"
            "\n"
            "RSM TABLE\n"
            "  1 ALL --- EXA TS 2000.00\n"
            "  1 ALL --- TRI TS 2000.00\n"
            "  1 1,2 --- DOB TS 2000.00\n"
            "  1 1,2,3,4 --- QTN TS 2000.00\n",
            encoding="utf-8",
        )
        resultado, _ = normalizar_reporte(ruta)
        assert "GAN" in resultado[1]["apuestas"]
        assert "SEG" in resultado[1]["apuestas"]
        assert "TER" not in resultado[1]["apuestas"]
        assert "EXA" in resultado[1]["apuestas"]
        assert resultado[1]["apuestas"]["EXA"] is None
        assert resultado[1]["bases"]["EXA"] == 2000.0
        assert resultado[1]["bases"]["TRI"] == 2000.0


class TestPoolsVsBases:

    def test_tri_en_pools_no_en_rsm(self, tmp_path: Path):
        ruta = tmp_path / "card10.txt"
        ruta.write_text(
            "    10  GAN       SEG       TER  1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9\n"
            "        EXA       TRI\n"
            "        CUA\n"
            "        DOB( 10,11 )\n"
            "        QTP( 10,11,12,13,14 )\n"
            "\n"
            "RSM TABLE\n"
            "  1 10 --- EXA TS 2000.00\n"
            "  1 10 --- CUA TS 1000.00\n"
            "  1 10,11 --- DOB TS 2000.00\n"
            "  1 10,11,12,13,14 --- QTP TS 200.00\n",
            encoding="utf-8",
        )
        resultado, _ = normalizar_reporte(ruta)
        assert "TRI" in resultado[10]["apuestas"]
        assert resultado[10]["apuestas"]["TRI"] is None
        assert "TRI" not in resultado[10]["bases"]
        assert resultado[10]["bases"]["EXA"] == 2000.0


class TestCodigosEnPools:

    def test_linea_con_ter(self):
        from controlcomparador.parsers.report import _codigos_en_pools

        linea = (
            "     1  GAN       SEG       TER  1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9"
        )
        assert _codigos_en_pools(linea) == {"GAN", "SEG", "TER"}

    def test_linea_sin_ter(self):
        from controlcomparador.parsers.report import _codigos_en_pools

        linea = (
            "     1  GAN       SEG         1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9 1/9"
        )
        assert _codigos_en_pools(linea) == {"GAN", "SEG"}
        assert "TER" not in _codigos_en_pools(linea)


class TestNormalizarReportePalermo:

    def test_parsea_valores(self, ruta_reporte_palermo):
        valores, codigos_all = normalizar_reporte_palermo(ruta_reporte_palermo)
        assert len(valores) > 0

    def test_detecta_codigos_con_all(self, ruta_reporte_palermo):
        _, codigos_all = normalizar_reporte_palermo(ruta_reporte_palermo)
        assert "TRI" in codigos_all

    def test_exa_no_esta_en_codigos_all(self, ruta_reporte_palermo):
        _, codigos_all = normalizar_reporte_palermo(ruta_reporte_palermo)
        assert "EXA" not in codigos_all

    def test_tri_expandido_a_todas_carreras(self, ruta_reporte_palermo):
        valores, _ = normalizar_reporte_palermo(ruta_reporte_palermo)
        assert 1 in valores
        assert 2 in valores
        assert 3 in valores

    def test_valor_tri_igual_en_todas_por_all(self, ruta_reporte_palermo):
        valores, _ = normalizar_reporte_palermo(ruta_reporte_palermo)
        assert valores[1].get("TRI") == valores[2].get("TRI") == valores[3].get("TRI") == 1200.0
