## Proyecto: ControlComparador v2.0.0

**Raíz:** `C:\Users\cdiaz\Desktop\CONTROLCAMBIO`

### Arquitectura (v2, paquete modular)

```
controlcomparador/                    # Paquete Python moderno (14 módulos)
├── __init__.py                       # Versión 2.0.0
├── __main__.py                       # python -m controlcomparador
├── app.py                            # Typer CLI (5 comandos)
├── config.py                         # Constantes, regex, mapeos
├── models.py                         # Dataclasses
├── agent.py                          # AgenteComparacion wrapper
├── detector.py                       # Auto-detecta hipódromo y tipo PDF
├── parsers/
│   ├── pdf.py                        # San Isidro PDF + Palermo PDF + Tela Oficial
│   ├── report.py                     # RSM TABLE TXT
│   ├── posting.py                    # CARD POSTING PRICES TXT
│   └── planilla.py                   # La Plata XLS
├── comparators/
│   ├── san_isidro.py
│   ├── palermo.py
│   ├── laplata.py
│   └── posting.py
├── ui/
│   ├── console.py                    # Rich theme
│   ├── tables.py                     # Tablas Rich (soporta tipo_pdf)
│   └── menus.py                      # Menú interactivo
└── utils/
    └── money.py                      # Parseo de montos
```

### CLI Commands

```bash
python -m controlcomparador menu                                # Modo interactivo
python -m controlcomparador version                             # v2.0.0
python -m controlcomparador san-isidro --pdf X --reporte Y      # San Isidro (Oficial o Tela)
python -m controlcomparador palermo --bases X --reporte Y       # Palermo
python -m controlcomparador la-plata --planilla X --reporte Y   # La Plata
```

### Dependencias

```toml
dependencies = ["pypdf>=3.0", "xlrd>=2.0", "rich>=13.0", "typer>=0.9"]
```

### Comando compilar

```bash
pyinstaller ControlComparador.spec
```

### Módulos clave y sus funciones

#### parsers/report.py - RSM TABLE TXT
- `normalizar_reporte(ruta)` → `(dict, set)` — retorna tupla `(valores_por_carrera, codigos_con_all)` como `normalizar_reporte_palermo()`. Incluye apuestas que vienen solo del RSM TABLE (no solo del header). `codigos_con_all` trackea códigos con `ALL` race_map para excluirlos de `solo_en_reporte`.
- `validar_pick_conflict(datos_reporte)` — verifica que ninguna carrera tenga dos apuestas pick (TPL/QTN/QTP/CAD) juntas, ya que son mutuamente excluyentes.

#### parsers/pdf.py - Tela Oficial
- `es_tela_oficial(ruta)` — detecta por "Programa Depurado" en texto
- `_obtener_apuestas_tela_oficial(ruta)` — extrae apuestas anclado por líneas `APUESTAS:` (no por `Premio`), soporta "Clásico" como header de carrera
- `_parsear_bets_tela(texto)` — parsea línea "Nombre $ Valor, ..." con filtros:
  - **`es_apuesta_excluida(nombre)`**: excluye pases que no son 1er.Pase (2do–6to, último, final) pero mantiene 1er.Pase y Final 1er.Pase. Refuerzo con `PATRON_PASE_TELA`: si matchea pase distinto de 1er → excluir. Ver bug fix "último Pase encoding" abajo.
  - **`APUESTAS_SIN_COMPARAR_VALOR`**: GAN/SEG/TER se extraen con valor vacío (solo presencia)
- `extraer_pases_tela_oficial(ruta)` — extrae pases de tela oficial. Busca líneas después de "Bolsa Total:" y antes del nro de carrera, parsea apuestas pick con `$ Valor` y pase name (1er.Pase, 2do.Pase, etc.). Usa `_normalizar_pase()` para formato consistente. Retorna `dict[int, dict[str, set[str]]]` → `{nro_carrera: {codigo: {pase_name, ...}}}`
- `_normalizar_pase(texto)` — normaliza nombres de pase: "1er.Pase", "2do.Pase", "3er.Pase", "4to.Pase", "5to.Pase", "Último.Pase", "Final.1er.Pase"
- `obtener_apuestas_por_carrera(ruta)` — auto-detecta: tela oficial → `_obtener_apuestas_tela_oficial()`, otro → `_obtener_apuestas_programa_oficial()`
- `extraer_info_reunion_tela(ruta)` — extrae `{"reunion": "54", "fecha": "14/06/2026", "hipodromo": "..."}` desde página 1 del PDF para el HTML export

#### config.py
- `APUESTAS_SIN_COMPARAR_VALOR = {"GAN", "SEG", "TER"}` — códigos que solo se comparan en existencia
- `APUESTAS_PICK = {"TPL", "QTN", "QTP", "CAD"}` — apuestas pick mutuamente excluyentes por carrera
- `APUESTAS_IGNORAR_LAPLATA = {"GAN", "SEG", "TER", "QTN"}` — ignoradas del lado reporte en La Plata
- `PASES_POR_APUESTA = {"TPL": ["1er.Pase", "2do.Pase", "3er.Pase"], ...}` — dict de código → lista ordenada de pases esperados
- `PASE_ORDER = ["1er.Pase", "2do.Pase", "3er.Pase", "4to.Pase", "5to.Pase", "Último.Pase", "Final.1er.Pase"]` — orden global de todos los pases posibles
- `PATRON_EXCLUIR_PASE_SIN_FINAL` — excluye 2do–6to y **último** pase; patrón `[úu]?ltimo` tolera encoding corrupto de pypdf (`Cuaternaltimo`, `Iltimo`, ``)
- `PATRON_PASE_TELA` — detecta picks en líneas de pase; incluye `(?:selectivo\s+)?` para "Triplo Selectivo 1er.Pase"
- `PATRON_FINAL` — detecta "Final"
- `PATRON_PRIMER_PASE` — detecta "1er.Pase"

#### detector.py
- `_clasificar_pdf(ruta)` — detecta "Programa Depurado" → `"san_isidro"` (tela oficial usa mismo comparador)

#### agent.py
- `comparar_san_isidro()` — retorna `tipo_pdf: "TELA OFICIAL"` o `"OFICIAL"` según `es_tela_oficial()`

#### app.py
- Menú San Isidro opción 5: "Resumen de tela oficial (PDF)"
- `_resumen_tela_interactivo()` — selecciona PDF tela oficial, muestra BASES POR APUESTA + VALIDACIONES, pregunta ¿Guardar HTML? → guarda en Escritorio y abre navegador
- `_comparar_san_isidro_interactivo()` — flujo completo: selecciona PDF + reporte, compara, muestra tipo_pdf
- Extrae pases con `extraer_pases_tela_oficial()` y los mergea en los datos para validación de secuencias

#### ui/tables.py
- Tabla dinámica: título y columna "OFICIAL" vs "TELA OFICIAL" según `tipo_pdf`
- `imprimir_resumen_tela(datos, ruta)` — muestra archivo + BASES POR APUESTA + RESUMEN BASES ÚNICAS + VALIDACIONES + CONTROL DE PASES (Rich tables)
- `exportar_resumen_html(datos, ruta_pdf, ruta_salida)` — genera HTML standalone con marco verde, columnas 50/20/30%, width fit-content. Header "Reunión X — fecha — Hipódromo". Incluye secuencias de pases y resumen de bases únicas. Abre navegador automáticamente
- `_mostrar_bases_por_apuesta(datos)` — tabla Rich agrupando apuestas por código+valor con formato "ALL" o rangos (1-8,10-13)
- `_mostrar_resumen_bases_unicas(datos)` — debajo de BASES POR APUESTA, muestra en rojo las apuestas que tienen UN SOLO valor base (ej. "EXA: todas son de 2000"). Excluye GAN/SEG/TER (presencia)
- `_validar_carreras_tela(datos)` — valida reglas: EXA ↔ IMP según caballos, TRI ↔ CUA exclusión, pick conflict (TPL/QTN/QTP/CAD), etc.
- `_agrupar_pases_por_secuencia(datos)` — analiza pases desde cada 1er.Pase, agrupa por código de apuesta, muestra start→end carreras y marca COMPLETA/INCOMPLETA
- `_mostrar_validacion_pases(datos)` — tabla Rich por apuesta (TPL/QTN/QTP/CAD) mostrando secuencias de pases, carreras start→end, y estado COMPLETA (verde) / INCOMPLETA (amarillo con faltantes)
- `_format_carreras_list(carreras, total)` — "ALL", "1-3,5,7-9"

### Reglas de negocio importantes

- **Tela Oficial San Isidro**: anclaje por `APUESTAS:` (no `Premio`). Las líneas después de "Bolsa Total:" y antes del número de carrera son "extra bets" (pases). Se filtran con `es_apuesta_excluida()`. GAN/SEG/TER se extraen como presencia (None), no como valor.
- **La Plata:** CUATERNA = QTN, CUATRIFECTA = CUA (al revés que otros hipódromos)
- **San Isidro:** GAN, SEG, TER solo se comparan en existencia, no en valor
- **Palermo:** Si EXA/TRI aparece UNA sola vez en el PDF, se expande a todas las carreras (regla "ALL si única línea")
- **Posting:** El segundo archivo TXT sobrescribe al primero en caso de conflicto
- **Apuestas Pick:** TPL, QTN, QTP y CAD son mutuamente excluyentes por carrera. `validar_pick_conflict()` en `parsers/report.py` detecta >1 pick en la misma carrera.
- **ALL race_map en comparación presencia:** Cuando el RSM TABLE usa `ALL` para un código (ej. `ALL --- EXA 2000`), el código se agrega a `codigos_con_all` y se excluye del check `solo_en_reporte`. Aplica en San Isidro, La Plata y Palermo oficial.
- **Resumen de bases únicas (tela oficial):** `_mostrar_resumen_bases_unicas()` en `ui/tables.py` muestra en rojo las apuestas que tienen exactamente un solo valor base en todas las carreras (ej. "EXA: todas son de 2000"). Excluye GAN/SEG/TER (presencia).
- **Secuencias de pases:** Las apuestas pick (TPL=3p, QTN=4p, QTP=5p, CAD=6p) se validan por secuencias. Cada 1er.Pase inicia una secuencia que debe completarse con los pases siguientes (2do, 3er, etc.). Se considera COMPLETA si aparecen todos los pases esperados consecutivamente, INCOMPLETA si faltan algunos.

### Comparadores

#### comparators/san_isidro.py
- `comparar_pdf_y_reporte()` — desempaqueta `normalizar_reporte()` como `(dict, set)`. Excluye `codigos_con_all` de `solo_en_reporte` (línea 45). Integra `validar_pick_conflict()`.

#### comparators/palermo.py
- `comparar_oficial_palermo_con_reporte()` — excluye `codigos_con_all` de `solo_en_reporte`.

#### comparators/laplata.py
- `comparar_planilla_con_reporte()` — desempaqueta `normalizar_reporte()` como `(dict, set)`. Excluye `codigos_con_all` y `APUESTAS_IGNORAR_LAPLATA` de `solo_en_reporte`. Integra `validar_pick_conflict()`.

#### comparators/posting.py
- `comparar_posting_con_reporte()` — excluye `codigos_con_all` de ambos lados.

### Bugs fixes conocidos

**Falso positivo EXA/TRI en Carrera 7 (Palermo):**
- `normalizar_reporte_palermo()` retorna tupla `(valores_por_carrera, codigos_con_all)`
- `comparar_oficial_palermo_con_reporte()` excluye `codigos_con_all` de `solo_en_reporte`
- `comparar_posting_con_reporte()` excluye `codigos_con_all` de ambos lados

**Falso positivo EXA/TRI con ALL race_map en San Isidro / La Plata:**
- `normalizar_reporte()` ahora retorna `(dict, set)` como Palermo
- `comparar_pdf_y_reporte()` excluye `codigos_con_all` de `solo_en_reporte`
- `comparar_planilla_con_reporte()` excluye `codigos_con_all` de `solo_en_reporte`

**Detección de apuestas pick conflictivas (TPL/QTN/QTP/CAD):**
- `validar_pick_conflict()` en `parsers/report.py` chequea que ninguna carrera tenga dos o más picks
- Integrado en `comparar_pdf_y_reporte()`, `comparar_planilla_con_reporte()` y `_validar_carreras_tela()`

**Falsos positivos picks en tela oficial (último Pase / encoding PDF) — julio 2026:**
- **Síntoma:** comparación TELA vs REPORTE reportaba picks "solo en PDF" (QTN, CAD, TPL, QTP) en carreras donde la tela no los tenía como apuesta base (ej. C4, C6, C7, C8, C10).
- **Causa:** líneas `extra_bets` (post `Bolsa Total:`) listan pases en una sola línea comma-separated. pypdf extrae "Último Pase" corrupto (`Cuaternaltimo`, `Iltimo`, carácter ``) y el regex `ultimo\s+pase` no excluía esas entradas; `_parsear_bets_tela()` las agregaba como apuestas con valor `None`.
- **Fix:** `PATRON_EXCLUIR_PASE_SIN_FINAL` ampliado (`6to.Pase`, `[úu]?ltimo`); `PATRON_PASE_TELA` con `selectivo` y mismo último flexible; `es_apuesta_excluida()` excluye si `PATRON_PASE_TELA` matchea y el pase ≠ 1er.Pase.
- **Alcance:** aplica a **todos** los flujos (menú manual San Isidro, auto-detect, CLI `san-isidro`, resumen tela, OFICIAL vs POSTING) porque todos usan `obtener_apuestas_por_carrera()` → `_obtener_apuestas_tela_oficial()`.
- **Tests:** `tests/test_tela_oficial.py` (exclusión, líneas extra, integración con PDF real).
- **Regla de negocio:** solo `1er.Pase` con `$` en extra_bets cuenta como pick base de esa carrera; 2do–6to y último son solo secuencia de pases (`extraer_pases_tela_oficial()`).

### Próximas mejoras planeadas

- Modo batch para procesar múltiples hipódromos

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **CONTROLCAMBIO** (553 symbols, 1213 relationships, 47 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/CONTROLCAMBIO/context` | Codebase overview, check index freshness |
| `gitnexus://repo/CONTROLCAMBIO/clusters` | All functional areas |
| `gitnexus://repo/CONTROLCAMBIO/processes` | All execution flows |
| `gitnexus://repo/CONTROLCAMBIO/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
