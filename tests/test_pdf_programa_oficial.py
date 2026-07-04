# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, patch

from controlcomparador.parsers.pdf import (
    _obtener_apuestas_programa_oficial,
    normalizar_desde_lista_apuestas,
)


def _pagina_programa(texto: str) -> MagicMock:
    pagina = MagicMock()
    pagina.extract_text.return_value = texto
    return pagina


@patch("controlcomparador.parsers.pdf.obtener_caballos_por_carrera", return_value={13: 16})
@patch("pypdf.PdfReader")
def test_imperfecta_extra_con_ganador_toma_valor(mock_reader, _mock_caballos):
    mock_reader.return_value.pages = [
        _pagina_programa(
            "13ª - Premio LA JOLLA 2010 - 19:50 hs.\n"
            "APUESTAS: Ganador, Segundo, Tercero, Imperfecta Extra $ 5000, Cuatrifecta $ 2000\n"
        )
    ]
    raw = _obtener_apuestas_programa_oficial("fake.pdf")
    datos = normalizar_desde_lista_apuestas(raw)
    assert datos[13]["apuestas"]["IMP"] == 5000.0
    assert datos[13]["apuestas"]["CUA"] == 2000.0
    assert datos[13]["apuestas"]["GAN"] is None


@patch("controlcomparador.parsers.pdf.obtener_caballos_por_carrera", return_value={1: 9})
@patch("pypdf.PdfReader")
def test_ganador_seg_ter_sin_valor_en_apuestas_separadas(mock_reader, _mock_caballos):
    mock_reader.return_value.pages = [
        _pagina_programa(
            "1ª - Premio TEST - 14:00 hs.\n"
            "APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000, Trifecta $ 2000\n"
        )
    ]
    raw = _obtener_apuestas_programa_oficial("fake.pdf")
    datos = normalizar_desde_lista_apuestas(raw)
    assert datos[1]["apuestas"]["GAN"] is None
    assert datos[1]["apuestas"]["EXA"] == 2000.0
    assert datos[1]["apuestas"]["TRI"] == 2000.0
