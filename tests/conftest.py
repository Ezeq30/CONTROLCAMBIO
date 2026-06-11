from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def ruta_reporte_ejemplo() -> str:
    return str(FIXTURES_DIR / "reporte_ejemplo.txt")


@pytest.fixture
def ruta_reporte_palermo() -> str:
    return str(FIXTURES_DIR / "reporte_palermo.txt")


@pytest.fixture
def ruta_reporte_laplata() -> str:
    return str(FIXTURES_DIR / "reporte_laplata.txt")


@pytest.fixture
def ruta_reporte_posting() -> str:
    return str(FIXTURES_DIR / "reporte_posting.txt")


@pytest.fixture
def ruta_reporte_vacio() -> str:
    return str(FIXTURES_DIR / "reporte_vacio.txt")
