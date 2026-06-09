# ControlComparador v2.0.0

Comparador de archivos PDF (programa oficial) vs reportes TXT para apuestas hípicas — Hipódromo de San Isidro, Palermo y La Plata.

## Estructura del proyecto

```
controlcomparador/                    # Paquete Python moderno
├── __init__.py                       # Versión 2.0.0
├── __main__.py                       # Entry point: python -m controlcomparador
├── app.py                            # CLI con Typer (5 comandos)
├── config.py                         # Constantes, regex compilados, mapeos
├── models.py                         # Dataclasses (Carrera, Apuesta, etc.)
├── agent.py                          # AgenteComparacion (wrapper de alto nivel)
├── parsers/
│   ├── pdf.py                        # San Isidro PDF + Palermo PDF
│   ├── report.py                     # RSM TABLE TXT
│   ├── posting.py                    # CARD POSTING PRICES TXT
│   └── planilla.py                   # La Plata XLS
├── comparators/
│   ├── san_isidro.py                 # Comparación PDF vs Reporte
│   ├── palermo.py                    # Comparación Palermo + Oficial
│   ├── laplata.py                    # Comparación Planilla vs Reporte
│   └── posting.py                    # Comparación Posting vs Reporte
├── ui/
│   ├── console.py                    # Tema Rich personalizado
│   ├── tables.py                     # Tablas comparativas con Rich
│   └── menus.py                      # Menú interactivo mejorado
└── utils/
    └── money.py                      # Parseo de montos (monetarios)

carreras_desde_pdf.py                 # Archivo original (respaldo intacto, 2671 líneas)
pyproject.toml                        # Dependencias + script entry point
ControlComparador.spec                 # PyInstaller spec (apunta al paquete)
```

## CLI (Typer)

```bash
# Modo interactivo (experiencia clásica mejorada con Rich)
python -m controlcomparador menu

# Modo directo (CLI)
python -m controlcomparador san-isidro --pdf <path> --reporte <path> [--posting <path>...]
python -m controlcomparador palermo --bases <path> --reporte <path> [--oficial <path>] [--posting <path>...] [--fecha dd/mm/aaaa]
python -m controlcomparador la-plata --planilla <path> --reporte <path> [--posting <path>...]
python -m controlcomparador version
```

## Dependencias

```bash
pip install pypdf xlrd rich typer
```

## Compilar a .exe

```bash
pyinstaller ControlComparador.spec
```

Genera `dist/ControlComparador.exe`.

## Hipódromos soportados

### San Isidro
- Lee programa oficial PDF (extrae caballos y apuestas por carrera)
- Compara contra reporte TXT (RSM TABLE)

### Palermo
- Lee PDF de Bases y Apuestas Palermo (formato 2 columnas)
- Opcional: lee PDF oficial (solo presencia de apuestas)
- Compara contra reporte TXT (RSM TABLE)

### La Plata
- Lee planilla XLS (formato MAN/CAR/APUESTA/BASE)
- Compara contra reporte TXT (RSM TABLE)
- **Atención:** CUATERNA = QTN (no CUA). CUATRIFECTA = CUA.

### Posting Prices (todos los hipódromos)
- Lee 1 o 2 archivos TXT de CARD POSTING PRICES
- Compara valores contra RSM TABLE del reporte

## Bug conocido (ya fixeado)

**Falso positivo EXA/TRI en Carrera 7 (Palermo)**: Cuando un código tiene `race_map ALL` en RSM TABLE, se expande a todas las carreras pero se registra en `codigos_con_all`. Los comparadores que solo verifican presencia (no montos) excluyen esos códigos para evitar falsos positivos.
