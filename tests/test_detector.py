from unittest.mock import patch, MagicMock
from pathlib import Path

from controlcomparador.detector import (
    _clasificar_txt,
    _clasificar_pdf,
    detectar_archivos,
    hipodromos_detectados,
    resumen_deteccion,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestClasificarTxt:

    def test_reporte_con_rsm(self):
        ruta = FIXTURES_DIR / "reporte_only.txt"
        assert _clasificar_txt(ruta) == "reporte"

    def test_posting_sin_rsm(self):
        ruta = FIXTURES_DIR / "posting_only.txt"
        assert _clasificar_txt(ruta) == "posting"

    def test_archivo_generico(self):
        ruta = FIXTURES_DIR / "archivo_generico.txt"
        assert _clasificar_txt(ruta) is None

    def test_reporte_con_rsm_es_reporte_aunque_tenga_posting(self):
        ruta = FIXTURES_DIR / "reporte_con_posting.txt"
        assert _clasificar_txt(ruta) == "reporte"


class TestClasificarPdf:

    @patch("pypdf.PdfReader")
    def test_san_isidro_por_carrera_pdf(self, mock_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "1ª - Premio FLOWING RYE - 14:05 hs.\nAPUESTAS:"
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader.return_value = mock_instance
        assert _clasificar_pdf(Path("dummy.pdf")) == "san_isidro"

    @patch("pypdf.PdfReader")
    def test_palermo_bases_por_fila_palermo(self, mock_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "EXACTA ($ 500.00) 1-3\nTRIFECTA ($ 1200.00) 1-3"
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader.return_value = mock_instance
        assert _clasificar_pdf(Path("dummy.pdf")) == "palermo_bases"

    @patch("pypdf.PdfReader")
    def test_palermo_oficial_por_apuestas_a(self, mock_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "APUESTAS A: EXACTA, TRIFECTA\n1  Carrera"
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader.return_value = mock_instance
        assert _clasificar_pdf(Path("dummy.pdf")) == "palermo_oficial"

    @patch("pypdf.PdfReader")
    def test_palermo_bases_tiene_prioridad_sobre_apuestas_a(self, mock_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "EXACTA ($ 500.00) 1-3\nAPUESTAS A: EXACTA, TRIFECTA"
        )
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader.return_value = mock_instance
        assert _clasificar_pdf(Path("dummy.pdf")) == "palermo_bases"

    @patch("pypdf.PdfReader")
    def test_pdf_sin_patrones(self, mock_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Texto generico sin patrones"
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader.return_value = mock_instance
        assert _clasificar_pdf(Path("dummy.pdf")) == "pdf_desconocido"

    @patch("pypdf.PdfReader")
    def test_error_lectura_retorna_none(self, mock_reader):
        mock_reader.side_effect = Exception("Error de lectura")
        assert _clasificar_pdf(Path("dummy.pdf")) is None


class TestDetectarArchivos:

    def test_carpeta_inexistente(self):
        resultado = detectar_archivos("C:/ruta_que_no_existe_xyz")
        assert "error" in resultado

    def test_carpeta_vacia(self, tmp_path):
        resultado = detectar_archivos(tmp_path)
        assert hipodromos_detectados(resultado) == []

    def test_detecta_san_isidro_con_archivos(self, tmp_path):
        (tmp_path / "programa.pdf").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            mock_pdf.return_value = "san_isidro"
            resultado = detectar_archivos(tmp_path)

        assert hipodromos_detectados(resultado) == ["san_isidro"]
        assert resultado["san_isidro"]["pdf"] is not None
        assert resultado["san_isidro"]["reporte"] is not None

    def test_detecta_palermo_con_bases(self, tmp_path):
        (tmp_path / "bases.pdf").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            mock_pdf.return_value = "palermo_bases"
            resultado = detectar_archivos(tmp_path)

        assert hipodromos_detectados(resultado) == ["palermo"]
        assert resultado["palermo"]["bases_pdf"] is not None
        assert resultado["palermo"]["reporte"] is not None

    def test_detecta_palermo_con_oficial(self, tmp_path):
        (tmp_path / "bases.pdf").write_text("")
        (tmp_path / "oficial.pdf").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            def side_effect(ruta):
                name = ruta.name
                if "bases" in name:
                    return "palermo_bases"
                return "palermo_oficial"
            mock_pdf.side_effect = side_effect
            resultado = detectar_archivos(tmp_path)

        assert hipodromos_detectados(resultado) == ["palermo"]
        assert resultado["palermo"]["bases_pdf"] is not None
        assert resultado["palermo"]["oficial_pdf"] is not None

    def test_detecta_la_plata(self, tmp_path):
        (tmp_path / "planilla.xls").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")
        resultado = detectar_archivos(tmp_path)
        assert hipodromos_detectados(resultado) == ["la_plata"]

    def test_detecta_posting(self, tmp_path):
        (tmp_path / "programa.pdf").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")
        (tmp_path / "posting.txt").write_text("CARD POSTING PRICES\n  1 1 --- EXA TS 100.00\n\n\n")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            mock_pdf.return_value = "san_isidro"
            resultado = detectar_archivos(tmp_path)

        assert len(resultado["san_isidro"]["posting"]) == 1
        assert hipodromos_detectados(resultado) == ["san_isidro"]

    def test_multiples_hipodromos_san_isidro_y_la_plata(self, tmp_path):
        (tmp_path / "programa.pdf").write_text("")
        (tmp_path / "planilla.xls").write_text("")
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            mock_pdf.return_value = "san_isidro"
            resultado = detectar_archivos(tmp_path)

        disponibles = hipodromos_detectados(resultado)
        assert "san_isidro" in disponibles
        assert "la_plata" in disponibles

    def test_sin_reporte_no_hay_hipodromo(self, tmp_path):
        (tmp_path / "programa.pdf").write_text("")

        with patch("controlcomparador.detector._clasificar_pdf") as mock_pdf:
            mock_pdf.return_value = "san_isidro"
            resultado = detectar_archivos(tmp_path)

        assert hipodromos_detectados(resultado) == []

    def test_sin_pdf_no_hay_san_isidro(self, tmp_path):
        (tmp_path / "reporte.txt").write_text("RSM TABLE\n  1 1 --- EXA TS 500.00")
        resultado = detectar_archivos(tmp_path)
        assert "san_isidro" not in hipodromos_detectados(resultado)


class TestResumenDeteccion:

    def test_resumen_vacio(self):
        deteccion = {
            "san_isidro": {"pdf": None, "reporte": None, "posting": []},
            "palermo": {"bases_pdf": None, "oficial_pdf": None, "reporte": None, "posting": []},
            "la_plata": {"planilla": None, "reporte": None, "posting": []},
        }
        assert resumen_deteccion(deteccion) == {}

    def test_resumen_con_archivos(self, tmp_path):
        pdf = tmp_path / "prog.pdf"
        pdf.write_text("")
        reporte = tmp_path / "rep.txt"
        reporte.write_text("")
        deteccion = {
            "san_isidro": {"pdf": pdf, "reporte": reporte, "posting": []},
            "palermo": {"bases_pdf": None, "oficial_pdf": None, "reporte": None, "posting": []},
            "la_plata": {"planilla": None, "reporte": None, "posting": []},
        }
        resumen = resumen_deteccion(deteccion)
        assert "San Isidro" in resumen
        assert len(resumen["San Isidro"]) == 2
