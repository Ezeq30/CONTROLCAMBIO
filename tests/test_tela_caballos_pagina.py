# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from controlcomparador.parsers.pdf import (
    _contar_caballos_tela,
    _segmento_entre_apuestas,
    normalizar_desde_lista_apuestas,
    obtener_apuestas_por_carrera,
)

PDF_7953 = Path(
    r"c:\Users\cdiaz\Downloads\SI_-_PROGRAMA_OFICIAL_DEL_08-07-2026_(Total_de_Carreras_11)_7953.pdf"
)


def _linea_caballo(nro: int, nombre: str) -> str:
    return f"Stud Test (LP)  0S-  -  -  {nro}  {nombre}    57.0 Jockey Name Trainer Z. 5 Sire Dam"


class TestSegmentoCrossPage:
    def test_segmento_concatena_paginas(self):
        pagina1 = ["header", "APUESTAS: Ganador", "tail"]
        pagina2 = ["Pagina 2", "more", "APUESTAS: Siguiente"]
        paginas = [pagina1, pagina2]
        segmento = _segmento_entre_apuestas(paginas, 0, 1, 1, 2)
        assert segmento == ["APUESTAS: Ganador", "tail", "Pagina 2", "more"]

    def test_caballos_en_pagina_siguiente(self):
        pagina1 = [
            "APUESTAS: Ganador, Segundo, Tercero $ 2, Exacta $ 2000",
            "STUD 4 ULTIMAS CABALLO JOCKEY ENTRENADOR PELO-EDAD-PADRE-MADRE",
            "Bolsa Total: $ 5315000",
            "Doble $2000",
            " 3",
            "15:30 hs.",
        ]
        pagina2 = [
            "Pagina 2",
            "Programa Depurado",
            _linea_caballo(1, "UNO"),
            _linea_caballo(2, "DOS"),
            _linea_caballo(3, "TRES"),
            _linea_caballo(4, "CUATRO"),
            _linea_caballo(5, "CINCO"),
            _linea_caballo(6, "SEIS"),
            _linea_caballo(7, "SIETE"),
            _linea_caballo(8, "OCHO"),
            _linea_caballo(9, "NUEVE"),
            "Premio SIGUIENTE",
            "APUESTAS: Ganador",
        ]
        paginas = [pagina1, pagina2]
        segmento = _segmento_entre_apuestas(paginas, 0, 0, 1, pagina2.index("APUESTAS: Ganador"))
        assert _contar_caballos_tela(segmento) == 9


@pytest.mark.skipif(not PDF_7953.is_file(), reason="PDF de integración no disponible")
class TestPdfIntegracion7953:
    def test_carrera_3_tiene_caballos_tras_salto_pagina(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(PDF_7953))
        assert datos[3]["caballos"] == 10

    def test_once_carreras_con_conteo_positivo(self):
        datos = normalizar_desde_lista_apuestas(obtener_apuestas_por_carrera(PDF_7953))
        assert len(datos) == 11
        assert all(datos[c]["caballos"] > 0 for c in datos)
