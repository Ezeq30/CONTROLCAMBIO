from controlcomparador.config import (
    MAPEO_ABREVIATURAS,
    MAPEO_RSM,
    MAPEO_RSM_SIN_WPS,
    APUESTAS_SIN_COMPARAR_VALOR,
    APUESTAS_IGNORAR_LAPLATA,
    CODIGOS_APUESTA_VALIDOS,
    ORDEN_APUESTAS,
)


class TestMapeos:

    def test_mapeo_abreviaturas_ganador(self):
        assert MAPEO_ABREVIATURAS["ganador"] == "GAN"

    def test_mapeo_abreviaturas_exacta(self):
        assert MAPEO_ABREVIATURAS["exacta"] == "EXA"

    def test_mapeo_abreviaturas_trifecta(self):
        assert MAPEO_ABREVIATURAS["trifecta"] == "TRI"

    def test_mapeo_abreviaturas_cuaterna(self):
        assert MAPEO_ABREVIATURAS["cuaterna"] == "QTN"

    def test_mapeo_abreviaturas_cuatrifecta(self):
        assert MAPEO_ABREVIATURAS["cuatrifecta"] == "CUA"

    def test_mapeo_abreviaturas_doble(self):
        assert MAPEO_ABREVIATURAS["doble"] == "DOB"

    def test_mapeo_abreviaturas_triplo(self):
        assert MAPEO_ABREVIATURAS["triplo"] == "TPL"

    def test_mapeo_abreviaturas_imperfecta(self):
        assert MAPEO_ABREVIATURAS["imperfecta"] == "IMP"

    def test_mapeo_abreviaturas_quintuplo(self):
        assert MAPEO_ABREVIATURAS["quintuplo"] == "QTP"

    def test_mapeo_abreviaturas_cadena(self):
        assert MAPEO_ABREVIATURAS["cadena"] == "CAD"

    def test_mapeo_abreviaturas_segundo(self):
        assert MAPEO_ABREVIATURAS["segundo"] == "SEG"

    def test_mapeo_abreviaturas_tercero(self):
        assert MAPEO_ABREVIATURAS["tercero"] == "TER"

    def test_mapeo_rsm_exa(self):
        assert MAPEO_RSM["EXA"] == "EXA"

    def test_mapeo_rsm_wps_es_none(self):
        assert MAPEO_RSM["WPS"] is None

    def test_mapeo_rsm_sin_wps_tiene_exa(self):
        assert MAPEO_RSM_SIN_WPS["EXA"] == "EXA"

    def test_mapeo_rsm_sin_wps_no_tiene_wps(self):
        assert "WPS" not in MAPEO_RSM_SIN_WPS


class TestCodigosValidos:

    def test_todos_los_codigos_estan_en_orden(self):
        for codigo in ORDEN_APUESTAS:
            assert codigo in CODIGOS_APUESTA_VALIDOS


class TestApuestasSinCompararValor:

    def test_gan_esta_en_sin_comparar(self):
        assert "GAN" in APUESTAS_SIN_COMPARAR_VALOR

    def test_seg_esta_en_sin_comparar(self):
        assert "SEG" in APUESTAS_SIN_COMPARAR_VALOR

    def test_ter_esta_en_sin_comparar(self):
        assert "TER" in APUESTAS_SIN_COMPARAR_VALOR

    def test_exa_no_esta_en_sin_comparar(self):
        assert "EXA" not in APUESTAS_SIN_COMPARAR_VALOR


class TestApuestasIgnorarLaplata:

    def test_gan_ignorado(self):
        assert "GAN" in APUESTAS_IGNORAR_LAPLATA

    def test_seg_ignorado(self):
        assert "SEG" in APUESTAS_IGNORAR_LAPLATA

    def test_ter_ignorado(self):
        assert "TER" in APUESTAS_IGNORAR_LAPLATA

    def test_qtn_ignorado(self):
        assert "QTN" in APUESTAS_IGNORAR_LAPLATA

    def test_exa_no_ignorado(self):
        assert "EXA" not in APUESTAS_IGNORAR_LAPLATA
