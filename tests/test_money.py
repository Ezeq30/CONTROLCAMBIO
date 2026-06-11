from controlcomparador.utils.money import parsear_monto_str


class TestParsearMontoStr:

    def test_valor_entero_simple(self):
        assert parsear_monto_str("500") == 500.0

    def test_valor_decimal_punto(self):
        assert parsear_monto_str("500.50") == 500.50

    def test_punto_como_separador_miles(self):
        assert parsear_monto_str("5.000") == 5000.0

    def test_coma_como_decimal_europeo(self):
        assert parsear_monto_str("1000,50") == 1000.5

    def test_formato_mixto_miles_y_decimal(self):
        assert parsear_monto_str("1.000,50") == 1000.5

    def test_miles_con_tres_digitos(self):
        assert parsear_monto_str("12.500") == 12500.0

    def test_miles_con_decimal_europeo(self):
        assert parsear_monto_str("12.500,75") == 12500.75

    def test_valor_grande_sin_separador(self):
        assert parsear_monto_str("100000") == 100000.0

    def test_none_retorna_none(self):
        assert parsear_monto_str(None) is None

    def test_string_vacio_retorna_none(self):
        assert parsear_monto_str("") is None

    def test_string_solo_espacios_retorna_none(self):
        assert parsear_monto_str("   ") is None

    def test_texto_no_numerico_retorna_none(self):
        assert parsear_monto_str("abc") is None

    def test_cero(self):
        assert parsear_monto_str("0") == 0.0

    def test_valor_con_espacios(self):
        assert parsear_monto_str("  500  ") == 500.0

    def test_formato_argentino(self):
        assert parsear_monto_str("1.500,00") == 1500.0

    def test_valor_negativo(self):
        assert parsear_monto_str("-500") == -500.0

    def test_flotante_simple(self):
        assert parsear_monto_str("99.99") == 99.99
