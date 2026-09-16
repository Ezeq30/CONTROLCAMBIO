# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Optional

import re

from controlcomparador.config import (
    PATRON_CARRERA_PDF,
    PATRON_APUESTA_VALOR,
    PATRON_EXCLUIR_PASE_SIN_FINAL,
    PATRON_FINAL,
    PATRON_PRIMER_PASE,
    PATRON_PASE_TELA,
    PATRON_ULTIMO_PASE,
    PATRON_LINEA_APUESTA,
    PATRON_CABALLO,
    PATRON_FECHA,
    PATRON_FILA_PALERMO,
    PATRON_APUESTAS_A,
    PATRON_CARRERA_OFICIAL,
    PATRON_CARRERA_TELA_REPORTE,
    PATRON_DORSAL_TELA_REPORTE,
    PATRON_HEADER_STUD_TELA_REPORTE,
    PATRON_PROGRAMA_DEPURADO,
    PATRON_PROGRAMA_OFICIAL_REPORTE,
    PATRON_REUNION_TELA_REPORTE,
    MAPEO_ABREVIATURAS,
    CODIGOS_APUESTA_VALIDOS,
    APUESTAS_SIN_COMPARAR_VALOR,
)
from controlcomparador.utils.money import parsear_monto_str


def es_apuesta_excluida(nombre: str) -> bool:
    if not nombre:
        return False
    low = nombre.strip().lower()
    # Doble sin pase (tela vieja "Doble $2000") se incluye.
    # Doble con pase distinto de 1er/1° (REPORTE PROGRAMA OFICIAL) se excluye.
    if low.startswith("doble"):
        if "pase" not in low and not PATRON_ULTIMO_PASE.search(nombre):
            return False
        if PATRON_PRIMER_PASE.search(nombre):
            return False
        return True
    if PATRON_EXCLUIR_PASE_SIN_FINAL.search(nombre):
        return True
    m_pase = PATRON_PASE_TELA.search(nombre)
    if m_pase and not PATRON_PRIMER_PASE.search(m_pase.group(2)):
        return True
    if PATRON_FINAL.search(nombre):
        if PATRON_PRIMER_PASE.search(nombre):
            return False
        return True
    return False


def normalizar_nombre_apuesta(nombre: str) -> str:
    nombre = nombre.strip()
    if not nombre:
        return nombre
    palabras = nombre.split()
    if not palabras:
        return nombre
    primera_palabra = palabras[0]
    if "pase" in nombre.lower() or primera_palabra.lower() in MAPEO_ABREVIATURAS:
        return primera_palabra
    return nombre


def abreviar_apuesta(nombre: str) -> str:
    nombre = (nombre or "").strip()
    if not nombre:
        return nombre
    clave = nombre.lower()
    if clave in MAPEO_ABREVIATURAS:
        return MAPEO_ABREVIATURAS[clave]
    # Imperfecta / Imperfecta extra / Imperfecta(Extra) → IMP
    if "imperfecta" in clave:
        return "IMP"
    return MAPEO_ABREVIATURAS.get(clave.split()[0], nombre)


def obtener_carreras_por_pagina(ruta_pdf: str | Path) -> list[dict]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []
    for num_pagina in range(len(reader.pages)):
        pagina_actual = num_pagina + 1
        texto = reader.pages[num_pagina].extract_text() or ""
        numero_carrera = None
        nombre_carrera = None
        m = PATRON_CARRERA_PDF.search(texto)
        if m:
            numero_carrera = int(m.group(1))
            nombre_carrera = m.group(2).strip()
            nombre_carrera = " ".join(nombre_carrera.split())
        resultado.append({
            "pagina": pagina_actual,
            "numero_carrera": numero_carrera,
            "nombre_carrera": nombre_carrera,
        })
    return resultado


def obtener_caballos_por_carrera(ruta_pdf: str | Path) -> dict[int, int]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado: dict[int, int] = {}
    ultima_carrera: int | None = None
    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        m_carrera = PATRON_CARRERA_PDF.search(texto)
        if m_carrera:
            ultima_carrera = int(m_carrera.group(1))
            numeros_caballos = set()
            for m in PATRON_CABALLO.finditer(texto):
                num = int(m.group(1))
                if 1 <= num <= 24:
                    numeros_caballos.add(num)
            cantidad = max(numeros_caballos) if numeros_caballos else 0
            resultado[ultima_carrera] = cantidad
        elif ultima_carrera is not None:
            for m in PATRON_CABALLO_TELA.finditer(texto):
                num = int(m.group(1))
                if 1 <= num <= 24:
                    resultado[ultima_carrera] = max(resultado.get(ultima_carrera, 0), num)
    return resultado


def _obtener_apuestas_programa_oficial(ruta_pdf: str | Path) -> list[list]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []
    caballos_por_carrera = obtener_caballos_por_carrera(ruta_pdf)
    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        m_carrera = PATRON_CARRERA_PDF.search(texto)
        if not m_carrera:
            continue
        num_carrera = int(m_carrera.group(1))
        cantidad_caballos = caballos_por_carrera.get(num_carrera, 0)
        lineas = texto.split("\n")
        bloque_apuestas = []
        for i, lin in enumerate(lineas):
            if "APUESTAS:" in lin.upper():
                idx = lin.upper().index("APUESTAS:")
                linea_inicial = lin[idx + len("APUESTAS:"):].strip()
                if linea_inicial:
                    bloque_apuestas.append(linea_inicial)
                max_lineas_continuacion = 6
                j = i + 1
                while j < len(lineas) and len(bloque_apuestas) < (1 + max_lineas_continuacion):
                    sig = lineas[j].strip()
                    if not sig:
                        break
                    if not PATRON_LINEA_APUESTA.search(sig):
                        break
                    bloque_apuestas.append(sig)
                    j += 1
                break
        texto_apuestas = " ".join(bloque_apuestas)
        if not texto_apuestas:
            continue
        for m in PATRON_APUESTA_VALOR.finditer(texto_apuestas):
            apuesta_bruta = m.group(1).strip().rstrip(",")
            valor = m.group(2).strip()
            if not apuesta_bruta or not valor:
                continue
            if "Ganador" in apuesta_bruta:
                partes = [p.strip() for p in apuesta_bruta.split(",") if p.strip()]
                for p in partes:
                    p_norm = normalizar_nombre_apuesta(p)
                    p_cod = abreviar_apuesta(p_norm)
                    if p_cod in CODIGOS_APUESTA_VALIDOS:
                        valor_ap = "" if p_cod in APUESTAS_SIN_COMPARAR_VALOR else valor
                        resultado.append([num_carrera, cantidad_caballos, p_cod, valor_ap])
                continue
            apuesta = apuesta_bruta
            if "," in apuesta:
                apuesta = apuesta.rsplit(",", 1)[-1].strip()
            if not es_apuesta_excluida(apuesta):
                apuesta_normalizada = normalizar_nombre_apuesta(apuesta)
                apuesta_cod = abreviar_apuesta(apuesta_normalizada)
                if apuesta_cod in CODIGOS_APUESTA_VALIDOS:
                    resultado.append([num_carrera, cantidad_caballos, apuesta_cod, valor])
    return resultado


# --- Tela Oficial San Isidro PDF ---

PATRON_BET_VALUE = re.compile(r"(.+?)\s*\$\s*([\d.,]+)")
PATRON_EXTRA_BETS = re.compile(
    r"(Cuaterna|Triplo|Quintuplo|Cadena|Doble|Imperfecta|Cuatrifecta)", re.IGNORECASE
)
PATRON_CABALLO_TELA = re.compile(r"\s+(\d+)\s{2,}(?:[A-Z]|')")


def es_tela_depurada(ruta_pdf: str | Path) -> bool:
    """Tela vieja: 'Programa Depurado' en la primera página."""
    import pypdf
    try:
        reader = pypdf.PdfReader(ruta_pdf)
        if not reader.pages:
            return False
        texto = reader.pages[0].extract_text() or ""
        return bool(PATRON_PROGRAMA_DEPURADO.search(texto))
    except Exception:
        return False


def es_tela_reporte_oficial(ruta_pdf: str | Path) -> bool:
    """Tela nueva: REPORTE PROGRAMA OFICIAL con headers 'Na PREMIO/CLÁSICO'."""
    import pypdf
    try:
        reader = pypdf.PdfReader(ruta_pdf)
        if not reader.pages:
            return False
        # No confundir con Programa Depurado (también puede decir "oficial" en el cuerpo).
        if PATRON_PROGRAMA_DEPURADO.search(reader.pages[0].extract_text() or ""):
            return False
        muestra = ""
        for p in reader.pages[:4]:
            muestra += (p.extract_text() or "") + "\n"
        if not PATRON_PROGRAMA_OFICIAL_REPORTE.search(muestra):
            return False
        return bool(PATRON_CARRERA_TELA_REPORTE.search(muestra))
    except Exception:
        return False


def es_tela_oficial(ruta_pdf: str | Path) -> bool:
    """True si es tela depurada o REPORTE PROGRAMA OFICIAL (ambas para resumen)."""
    return es_tela_depurada(ruta_pdf) or es_tela_reporte_oficial(ruta_pdf)


def tipo_tela_oficial(ruta_pdf: str | Path) -> str | None:
    """Etiqueta de formato: TELA DEPURADA | TELA PROGRAMA OFICIAL | None."""
    if es_tela_depurada(ruta_pdf):
        return "TELA DEPURADA"
    if es_tela_reporte_oficial(ruta_pdf):
        return "TELA PROGRAMA OFICIAL"
    return None


def _parsear_bets_tela(texto: str) -> list[tuple[str, str]]:
    """Parsea linea de apuestas formato tela: 'Nombre1 $ Valor, Nombre2 $ Valor'.
    Retorna [(codigo, valor_str), ...]."""
    resultado: list[tuple[str, str]] = []
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    for p in partes:
        m_val = re.search(r"\$\s*([\d.,]+)", p)
        if m_val:
            nombre = re.sub(r"\$\s*[\d.,]+", "", p).strip().rstrip(",")
            valor = m_val.group(1)
        else:
            nombre = p
            valor = ""
        if not nombre:
            continue
        if es_apuesta_excluida(nombre):
            continue
        codigo = abreviar_apuesta(normalizar_nombre_apuesta(nombre))
        if codigo and codigo in CODIGOS_APUESTA_VALIDOS:
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                resultado.append((codigo, ""))
            else:
                resultado.append((codigo, valor))
    return resultado


def _segmento_entre_apuestas(
    paginas: list[list[str]],
    start_pi: int,
    start_li: int,
    end_pi: int,
    end_li: int,
) -> list[str]:
    """Lineas desde APUESTAS actual (inclusive) hasta el siguiente (exclusive), cross-page."""
    if start_pi == end_pi:
        return paginas[start_pi][start_li:end_li]
    lineas: list[str] = []
    lineas.extend(paginas[start_pi][start_li:])
    for pi in range(start_pi + 1, end_pi):
        lineas.extend(paginas[pi])
    if end_pi < len(paginas):
        lineas.extend(paginas[end_pi][:end_li])
    return lineas


def _contar_caballos_tela(lineas: list[str]) -> int:
    horse_nums: set[int] = set()
    in_horse_block = False
    for l in lineas:
        s = l.strip()
        if "CHAQUETILLAS" in s:
            in_horse_block = False
            continue
        if re.search(r"\bCABALLO\b", s, re.IGNORECASE) and "JOCKEY" in s.upper():
            in_horse_block = True
            continue
        if in_horse_block:
            if not s or s.startswith("Bolsa") or s.startswith("Total") or s.startswith("*"):
                continue
            if s.isdigit():
                continue
            if re.match(r"\d{1,2}:\d{2}", s):
                continue
            m = PATRON_CABALLO_TELA.search(s)
            if m:
                num = int(m.group(1))
                if 1 <= num <= 30:
                    horse_nums.add(num)
    return len(horse_nums) if horse_nums else 0


def _numero_carrera_tela(
    paginas: list[list[str]],
    start_pi: int,
    start_li: int,
    race_lines: list[str],
) -> int | None:
    """En tela el nro de carrera suele ir DESPUÉS de APUESTAS/Bolsa (no antes).

    Si se busca hacia atrás primero, en páginas con 2 carreras se toma el nro
    de la carrera anterior (mezcla caballos/apuestas/pases).
    """
    for l in race_lines:
        s = l.strip()
        if s.isdigit() and 1 <= int(s) <= 30:
            return int(s)
    lineas_pag = paginas[start_pi]
    for back in range(start_li - 1, max(start_li - 15, -1), -1):
        s = lineas_pag[back].strip()
        if s.isdigit() and 1 <= int(s) <= 30:
            return int(s)
    return None


def _extraer_apuestas_y_extras_tela(race_lines: list[str]) -> tuple[str, list[str]]:
    texto_apuestas = ""
    for l in race_lines:
        s = l.strip()
        if s.upper().startswith("APUESTAS:"):
            texto_apuestas = s[len("APUESTAS:"):].strip()
            break

    extra_bets: list[str] = []
    found_bolsa = False
    for l in race_lines:
        s = l.strip()
        if "Bolsa Total:" in s:
            found_bolsa = True
            continue
        if found_bolsa:
            if s.isdigit() and 1 <= int(s) <= 30:
                break
            if "CHAQUETILLAS" in s:
                break
            if PATRON_EXTRA_BETS.search(s) and "$" in s:
                if s not in extra_bets:
                    extra_bets.append(s)

    return texto_apuestas, extra_bets


def _obtener_apuestas_tela_oficial(ruta_pdf: str | Path) -> list[list]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    paginas = [(p.extract_text() or "").split("\n") for p in reader.pages]

    apuestas_pos: list[tuple[int, int]] = []
    for pi, lineas in enumerate(paginas):
        for i, l in enumerate(lineas):
            if l.strip().upper().startswith("APUESTAS:"):
                apuestas_pos.append((pi, i))

    resultado: list[list] = []

    for idx, (start_pi, start_li) in enumerate(apuestas_pos):
        if idx + 1 < len(apuestas_pos):
            end_pi, end_li = apuestas_pos[idx + 1]
        else:
            end_pi = len(paginas) - 1
            end_li = len(paginas[end_pi]) if paginas else 0

        race_lines = _segmento_entre_apuestas(paginas, start_pi, start_li, end_pi, end_li)
        texto_apuestas, extra_bets = _extraer_apuestas_y_extras_tela(race_lines)

        num_carrera = _numero_carrera_tela(paginas, start_pi, start_li, race_lines)
        if num_carrera is None:
            continue

        num_caballos = _contar_caballos_tela(race_lines)
        apuestas_vistas: set[str] = set()

        if texto_apuestas:
            for cod, val in _parsear_bets_tela(texto_apuestas):
                if cod not in apuestas_vistas:
                    resultado.append([num_carrera, num_caballos, cod, val])
                    apuestas_vistas.add(cod)

        for eb in extra_bets:
            for cod, val in _parsear_bets_tela(eb):
                if cod not in apuestas_vistas:
                    resultado.append([num_carrera, num_caballos, cod, val])
                    apuestas_vistas.add(cod)

    return resultado


_PATRON_LINEA_BET_REPORTE = re.compile(
    r"^(Ganador|Segundo|Tercero|Exacta|Trifecta|"
    r"Imperfecta(?:\s*\(?\s*extra\s*\)?)?"
    r"|Cuatrifecta|Doble|Triplo|Cuaterna|Quintuplo|Cadena)\b(.*)$",
    re.IGNORECASE,
)


def _secuencia_caballos_valida(nums: set[int]) -> bool:
    """Ignora restos de encoding (p. ej. solo {1}) que no son una lista real."""
    if not nums:
        return False
    return max(nums) >= 4 or len(nums) >= 3


def _es_header_stud_tela(linea: str) -> bool:
    """True solo para encabezado de grilla, no para 'STUD GRR' / 'STUD ALDEA STA'."""
    return bool(PATRON_HEADER_STUD_TELA_REPORTE.search(linea.strip()))


def _mejor_conjunto_dorsales(
    actual: set[int] | None, candidato: set[int] | None
) -> set[int] | None:
    """Prefiere el conjunto con mayor dorsal máximo (lista más completa)."""
    if not candidato or not _secuencia_caballos_valida(candidato):
        return set(actual) if actual else None
    if not actual or not _secuencia_caballos_valida(actual):
        return set(candidato)
    if max(candidato) > max(actual):
        return set(candidato)
    if max(candidato) == max(actual) and len(candidato) > len(actual):
        return set(candidato)
    return set(actual)


def _principal_y_pending_secuencias(
    seqs: list[set[int]],
) -> tuple[set[int], set[int] | None]:
    """Elige la lista principal (mayor dorsal) y pending si hay overflow real."""
    if not seqs:
        return set(), None
    if len(seqs) == 1:
        return set(seqs[0]), None
    ordenadas = sorted(seqs, key=lambda s: (max(s), len(s)), reverse=True)
    principal = set(ordenadas[0])
    pending: set[int] | None = None
    for extra in ordenadas[1:]:
        # Suplentes u otro bloque chico con max <= principal: no es overflow de otra carrera
        if max(extra) >= max(principal) or (1 in extra and max(extra) >= 8):
            pending = _mejor_conjunto_dorsales(pending, extra)
    return principal, pending


def _secuencias_dorsales(lineas: list[str]) -> list[set[int]]:
    """Agrupa dorsales; nuevo bloque con 01 o tras header STUD/CHAQUETILLAS/SUPLENTES."""
    sequences: list[set[int]] = []
    current: set[int] = set()

    def _flush() -> None:
        nonlocal current
        if current:
            sequences.append(current)
            current = set()

    for l in lineas:
        s = l.strip()
        su = s.upper()
        if "CHAQUETILLAS" in su or su == "SUPLENTES" or _es_header_stud_tela(s):
            _flush()
            continue
        if PATRON_CARRERA_TELA_REPORTE.match(s) or su == "APUESTAS" or su.startswith("APUESTAS"):
            _flush()
            continue
        found = [
            int(m.group(1))
            for m in PATRON_DORSAL_TELA_REPORTE.finditer(s)
            if 1 <= int(m.group(1)) <= 24
        ]
        for num in found:
            if num == 1 and current and max(current) > 1:
                _flush()
                current = {1}
            else:
                current.add(num)
    _flush()
    return [s for s in sequences if _secuencia_caballos_valida(s)]


def _dorsales_en_race_lines(race_lines: list[str]) -> tuple[set[int], set[int] | None]:
    """Dorsales dentro del segmento de carrera (tras APUESTAS / antes o después de STUD).

    pypdf a menudo pone los caballos *después* del bloque APUESTAS y *antes* de STUD,
    o mezcla dos listas (esta carrera + la siguiente).
    """
    seqs = _secuencias_dorsales(race_lines)
    if not seqs:
        return set(), None
    if len(seqs) == 1:
        return set(seqs[0]), None
    return set(seqs[0]), set(seqs[1])


def _dorsales_post_stud(race_lines: list[str]) -> tuple[set[int], set[int] | None]:
    """Tras header STUD de grilla: primer bloque de dorsales y pending (siguiente 01…)."""
    after_stud = False
    primero: set[int] = set()
    segundo: set[int] = set()
    fase = 0  # 0=buscar, 1=primero, 2=segundo
    for l in race_lines:
        s = l.strip()
        su = s.upper()
        if _es_header_stud_tela(s):
            after_stud = True
            continue
        if not after_stud:
            continue
        if PATRON_CARRERA_TELA_REPORTE.match(s):
            break
        if "CHAQUETILLAS" in su or su == "SUPLENTES":
            if fase == 1 and primero:
                fase = 2
            continue
        for m in PATRON_DORSAL_TELA_REPORTE.finditer(s):
            num = int(m.group(1))
            if not (1 <= num <= 24):
                continue
            if fase == 0:
                fase = 1
                primero.add(num)
            elif fase == 1:
                if num == 1 and primero and max(primero) > 1:
                    fase = 2
                    segundo = {1}
                else:
                    primero.add(num)
            else:
                if num == 1 and segundo and max(segundo) > 1:
                    break
                segundo.add(num)
    p1 = primero if _secuencia_caballos_valida(primero) else set()
    p2 = segundo if _secuencia_caballos_valida(segundo) else None
    return p1, p2


def _contar_caballos_tela_reporte(
    prev_lines: list[str],
    race_lines: list[str],
    pending: set[int] | None,
    next_lines: list[str] | None = None,
    skip_first_seq: bool = False,
    prev_preheader: bool = False,
) -> tuple[int, set[int] | None, bool]:
    """Caballos de la carrera + pending + si se consumió el 1er bloque de la siguiente.

    Retorna (cantidad, pending_siguiente, consumio_primer_seq_next).
    """
    seqs_race = _secuencias_dorsales(race_lines)
    # Si la carrera anterior consumió un bloque vía lookahead, no saltar la lista
    # propia de ESTA carrera (01..N tras APUESTAS, p. ej. C2 del miércoles 23/9).
    if skip_first_seq and seqs_race:
        if len(seqs_race) >= 1 and 1 in seqs_race[0] and max(seqs_race[0]) >= 8:
            skip_first_seq = False
        else:
            seqs_race = seqs_race[1:]

    in_race, in_race_pending = _principal_y_pending_secuencias(seqs_race)

    post, post_pending = _dorsales_post_stud(race_lines)
    if skip_first_seq and post:
        post = set(seqs_race[0]) if seqs_race else set()
        post_pending = set(seqs_race[1]) if len(seqs_race) > 1 else None

    seqs_prev = _secuencias_dorsales(prev_lines)
    sin_propios = not in_race and not (post and _secuencia_caballos_valida(post))

    next_pending: set[int] | None = None
    vins_de_pending = bool(pending and _secuencia_caballos_valida(pending))
    if vins_de_pending:
        nums: set[int] | None = set(pending)  # type: ignore[arg-type]
    elif sin_propios and len(seqs_prev) >= 2:
        prev_a, prev_b = set(seqs_prev[-2]), set(seqs_prev[-1])
        # Lista partida: 01..k al final de prev + (k+1)..N al inicio de next (C2)
        if (
            next_lines
            and 1 in prev_b
            and max(prev_b) < max(prev_a)
            and max(prev_b) < 8
        ):
            nseqs_early = _secuencias_dorsales(next_lines)
            if (
                nseqs_early
                and _secuencia_caballos_valida(nseqs_early[0])
                and min(nseqs_early[0]) == max(prev_b) + 1
            ):
                nums = set(prev_b) | set(nseqs_early[0])
            else:
                # prev_b son suplentes de la anterior, no de esta carrera
                nums = None
        else:
            nums = prev_a
            next_pending = prev_b
    elif len(seqs_prev) == 1 and prev_preheader:
        # Caballos antes del header en la misma página (p. ej. C1 del miércoles 23/9)
        nums = set(seqs_prev[0])
    else:
        nums = None

    # Merge por max: no pisar pending más completo con in_race/post más corto
    nums = _mejor_conjunto_dorsales(nums, in_race if in_race else None)
    nums = _mejor_conjunto_dorsales(nums, post if post else None)

    # No pasar suplentes (bloque más corto tras lista principal) como overflow
    def _es_suplente_de(principal: set[int], extra: set[int] | None) -> bool:
        return bool(
            principal
            and extra
            and 1 in principal
            and max(extra) < max(principal)
        )

    if in_race_pending and not _es_suplente_de(in_race, in_race_pending):
        next_pending = _mejor_conjunto_dorsales(next_pending, in_race_pending)
    if post_pending and not _es_suplente_de(
        post if post else (in_race if in_race else set()),
        post_pending,
    ):
        next_pending = _mejor_conjunto_dorsales(next_pending, post_pending)

    # Carrera ya contada por pending: el in_race descartado (p. ej. 01-07 tras
    # SUPLENTES en C7) pasa a la siguiente (C8 vacía → 7 caballos).
    if (
        vins_de_pending
        and nums
        and in_race
        and _secuencia_caballos_valida(in_race)
        and 1 in in_race
        and max(in_race) < max(nums)
    ):
        next_pending = _mejor_conjunto_dorsales(next_pending, in_race)

    consumio_next = False
    # Lookahead solo si aún no hay conteo (no robar la siguiente si ya hay pending)
    if sin_propios and next_lines:
        nseqs = _secuencias_dorsales(next_lines)
        if nseqs and _secuencia_caballos_valida(nseqs[0]):
            nxt0 = set(nseqs[0])
            # Pending débil 01..k + dorsales k+1..N al inicio de la siguiente (misma lista partida)
            if (
                nums
                and 1 in nums
                and max(nums) < 8
                and min(nxt0) == max(nums) + 1
            ):
                nums = set(nums) | nxt0
            elif (
                not nums
                and len(nseqs) >= 2
                and 1 in nxt0
                and _secuencia_caballos_valida(nseqs[1])
                and 1 in nseqs[1]
                and max(nseqs[1]) >= max(nxt0)
            ):
                # Dos listas principales en next → 1ª es overflow de esta carrera
                nums = nxt0
                consumio_next = True
            # Si la 2ª es suplente más corta, no robar (C8 no toma los 8 de C9)

    if next_pending and not _secuencia_caballos_valida(next_pending):
        next_pending = None

    return (max(nums) if nums else 0), next_pending, consumio_next


def _parsear_linea_bet_reporte(linea: str) -> tuple[str, str] | None:
    """Una línea 'Exacta $2.000' / 'Quintuplo 1° Pase$1.000' → (nombre, valor)."""
    s = linea.strip()
    if not s or not _PATRON_LINEA_BET_REPORTE.match(s):
        return None
    m_val = re.search(r"\$\s*([\d.,]+)", s)
    valor = m_val.group(1) if m_val else ""
    nombre = re.sub(r"\$\s*[\d.,]+", "", s).strip()
    if not nombre:
        return None
    return nombre, valor


_PATRON_DORSAL_COL_CABALLO = re.compile(r"^(0[1-9]|1\d|2[0-4])$")


def _mul_affine(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    """Multiplica matrices afines 2D en forma (a,b,c,d,e,f)."""
    return (
        a[0] * b[0] + a[1] * b[2],
        a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2],
        a[2] * b[1] + a[3] * b[3],
        a[4] * b[0] + a[5] * b[2] + b[4],
        a[4] * b[1] + a[5] * b[3] + b[5],
    )


def _items_posicionados_pdf(ruta_pdf: str | Path) -> list[tuple[int, float, float, str]]:
    """Tokens de texto con posición (page, y, x, texto) vía visitor tm*cm."""
    import pypdf

    reader = pypdf.PdfReader(str(ruta_pdf))
    items: list[tuple[int, float, float, str]] = []
    for pi, page in enumerate(reader.pages):
        def _visitor(
            text: str,
            cm: list[float],
            tm: list[float],
            font_dict: object,
            font_size: float,
            _pi: int = pi,
        ) -> None:
            if not text or not text.strip():
                return
            m = _mul_affine(tuple(tm), tuple(cm))
            items.append((_pi, float(m[5]), float(m[4]), text.strip()))

        page.extract_text(visitor_text=_visitor)
    return items


def _secuencia_columna_caballo_ok(nums: set[int]) -> bool:
    """Columna CABALLO válida: empieza en 01 y llega contigua hasta el máximo."""
    if not nums or 1 not in nums:
        return False
    m = max(nums)
    return m >= 4 and len(nums) == m


def _detectar_carreras_posicionadas(
    items: list[tuple[int, float, float, str]],
) -> list[tuple[int, int, float]]:
    """Inicios de carrera (page, nro, y): dígito a la izquierda de 'a'.

    Contexto válido: Condición/mts debajo, o 'hs' cerca del título, o
    Condición en el tope de la página siguiente (carrera partida).
    """
    by_page: dict[int, list[tuple[float, float, str]]] = {}
    for pi, y, x, t in items:
        by_page.setdefault(pi, []).append((y, x, t))

    hallados: list[tuple[int, int, float]] = []
    for pi, toks in by_page.items():
        for y, _x, t in toks:
            m = PATRON_CARRERA_TELA_REPORTE.match(t)
            if m:
                hallados.append((pi, int(m.group(1)), y))

        for y, x, t in toks:
            if t.lower() not in ("a", "ª") or x > 70:
                continue
            best: tuple[float, int, float] | None = None
            for y2, x2, t2 in toks:
                if abs(y2 - y) > 18:
                    continue
                if not re.fullmatch(r"[1-9]|1[0-4]", t2):
                    continue
                if not (0 < (x - x2) < 30):
                    continue
                score = abs(x - x2) + abs(y2 - y)
                if best is None or score < best[0]:
                    best = (score, int(t2), y)
            if best is None:
                continue
            _score, nro, ry = best
            contexto = any(
                ("Condici" in t3 or "mts" in t3)
                and y3 < ry
                and (ry - y3) < 120
                for y3, _x3, t3 in toks
            )
            contexto = contexto or any(
                "hs" in t3.lower() and abs(y3 - ry) < 40 and x3 < 80
                for y3, x3, t3 in toks
            )
            if not contexto and (pi + 1) in by_page:
                contexto = any(
                    ("Condici" in t3 or "mts" in t3) and y3 > 700
                    for y3, _x3, t3 in by_page[pi + 1]
                )
            if contexto:
                hallados.append((pi, nro, ry))

    best_y: dict[tuple[int, int], float] = {}
    for pi, nro, y in hallados:
        key = (pi, nro)
        if key not in best_y or y > best_y[key]:
            best_y[key] = y
    out = [(pi, nro, y) for (pi, nro), y in best_y.items()]
    out.sort(key=lambda r: (r[0], -r[2], r[1]))
    return out


def _dorsales_en_banda_inferida(
    dorsales: list[tuple[int, float, float, int]],
    pi: int,
    ry: float,
    next_bound: tuple[int, float] | None,
    suplentes: list[tuple[int, float]],
) -> tuple[set[int], dict[int, int], set[int]]:
    """Sin header CABALLO usable: dorsales x∈[140,200] entre título y SUPLENTES."""
    nums: set[int] = set()
    per_page: dict[int, int] = {}
    for spi, sy in sorted(suplentes, key=lambda t: (t[0], -t[1])):
        after = (spi > pi) or (spi == pi and sy < ry)
        if not after:
            continue
        if next_bound is not None:
            npi, ny = next_bound
            before_next = (spi < npi) or (spi == npi and sy > ny)
            if not before_next:
                continue
        for dpi, dy, dx, n in dorsales:
            if dx < 5 or not (140 <= dx <= 200):
                continue
            in_band = False
            if dpi == pi == spi and sy < dy < ry:
                in_band = True
            elif dpi == pi and spi > pi and dy < ry:
                in_band = True
            elif pi < dpi < spi:
                in_band = True
            elif dpi == spi and spi > pi and dy > sy:
                in_band = True
            if in_band:
                nums.add(n)
                per_page[dpi] = per_page.get(dpi, 0) + 1
        break
    return nums, per_page, set(per_page)


def _contar_caballos_desde_items(
    items: list[tuple[int, float, float, str]],
) -> dict[int, int]:
    """Cuenta dorsales de la columna CABALLO hasta SUPLENTES (nunca debajo).

    Une headers CABALLO (x>=5) entre el título y la siguiente carrera.
    Si no hay header usable, infiere la columna por x∈[140,200].

    pypdf a veces deja dorsales en x≈0 (matriz rota). Se recuperan:
    - agujeros: huérfanos full en páginas con ≥3 hits; continuación solo 1..max;
    - extensión +1 si hay hueco vertical a SUPLENTES y huérfano max+1.
    """
    carreras = _detectar_carreras_posicionadas(items)
    if not carreras:
        return {}

    orden = sorted(carreras, key=lambda r: (r[0], -r[2], r[1]))
    vistas: set[int] = set()
    orden_unico: list[tuple[int, int, float]] = []
    for pi, nro, y in orden:
        if nro in vistas:
            continue
        vistas.add(nro)
        orden_unico.append((pi, nro, y))

    # Solo headers con posición real (x≈0 es basura de pypdf)
    headers_cab = [(pi, y, x) for pi, y, x, t in items if t == "CABALLO" and x >= 5]
    suplentes = [(pi, y) for pi, y, _x, t in items if t.upper() == "SUPLENTES"]
    dorsales = [
        (pi, y, x, int(t))
        for pi, y, x, t in items
        if _PATRON_DORSAL_COL_CABALLO.match(t)
    ]
    orphans_by_page: dict[int, set[int]] = {}
    for dpi, _dy, dx, n in dorsales:
        if dx < 5:
            orphans_by_page.setdefault(dpi, set()).add(n)

    caballos: dict[int, int] = {}
    for i, (pi, nro, ry) in enumerate(orden_unico):
        next_bound: tuple[int, float] | None = None
        if i + 1 < len(orden_unico):
            next_bound = (orden_unico[i + 1][0], orden_unico[i + 1][2])

        cands: list[tuple[int, float, float]] = []
        for hpi, hy, hx in headers_cab:
            after_title = (hpi > pi) or (hpi == pi and hy < ry)
            if not after_title:
                continue
            if next_bound is not None:
                npi, ny = next_bound
                before_next = (hpi < npi) or (hpi == npi and hy > ny)
                if not before_next:
                    continue
            cands.append((hpi, hy, hx))

        nums: set[int] = set()
        pages: set[int] = set()
        per_page_hits: dict[int, int] = {}
        last_ys: list[float] = []
        last_gaps: list[float] = []
        last_stop: float | None = None

        if cands:
            for hpi, hy, hx in sorted(cands, key=lambda t: (t[0], -t[1])):
                pages.add(hpi)
                stop_y = -1e9
                for spi, sy in suplentes:
                    if spi == hpi and sy < hy:
                        stop_y = max(stop_y, sy)
                for opi, oy, _ox in headers_cab:
                    if opi == hpi and oy < hy:
                        stop_y = max(stop_y, oy)

                ys_header: list[float] = []
                for dpi, dy, dx, n in dorsales:
                    if dpi != hpi or dx < 5:
                        continue
                    if abs(dx - hx) > 35:
                        continue
                    # Solo entre header y SUPLENTES (nunca debajo)
                    if not (stop_y < dy < hy):
                        continue
                    nums.add(n)
                    ys_header.append(dy)
                    per_page_hits[hpi] = per_page_hits.get(hpi, 0) + 1

                if ys_header:
                    ys_sorted = sorted(ys_header, reverse=True)
                    last_ys = ys_sorted
                    last_stop = stop_y
                    last_gaps = [
                        ys_sorted[j] - ys_sorted[j + 1]
                        for j in range(len(ys_sorted) - 1)
                    ]
        else:
            nums, per_page_hits, pages = _dorsales_en_banda_inferida(
                dorsales, pi, ry, next_bound, suplentes
            )

        # Agujeros: huérfanos x≈0
        if len(nums) >= 3 and not _secuencia_columna_caballo_ok(nums):
            m = max(nums)
            holes = set(range(1, m + 1)) - nums
            main_pages = {p for p, c in per_page_hits.items() if c >= 3}
            for p in pages:
                orph = orphans_by_page.get(p, set())
                if p in main_pages:
                    nums |= orph
                else:
                    nums |= orph & holes

        # Extender +1 si hay hueco vertical hasta SUPLENTES y huérfano max+1
        if (
            _secuencia_columna_caballo_ok(nums)
            and last_ys
            and last_stop is not None
            and last_stop > -1e8
        ):
            med = median(last_gaps) if last_gaps else 35.0
            room = min(last_ys) - last_stop
            m = max(nums)
            if room >= med * 1.5 and any(
                (m + 1) in orphans_by_page.get(p, set()) for p in pages
            ):
                nums.add(m + 1)

        if _secuencia_columna_caballo_ok(nums):
            caballos[nro] = max(nums)

    return caballos


def _caballos_por_columna_caballo(ruta_pdf: str | Path) -> dict[int, int]:
    """Cantidad de caballos por carrera leyendo la columna CABALLO del PDF."""
    try:
        items = _items_posicionados_pdf(ruta_pdf)
    except Exception:
        return {}
    return _contar_caballos_desde_items(items)


def _extraer_bloque_apuestas_reporte(race_lines: list[str]) -> list[str]:
    """Líneas de apuesta del segmento de carrera.

    pypdf puede partir el bloque: parte de las apuestas arriba y Exacta/TRI
    después de los caballos. Se toman todas las líneas que matchean apuesta,
    no solo el tramo contiguo tras ``APUESTAS``.
    """
    out: list[str] = []
    for l in race_lines:
        s = l.strip()
        if not s:
            continue
        if _PATRON_LINEA_BET_REPORTE.match(s):
            out.append(s)
    return out


def _obtener_apuestas_tela_reporte_oficial(ruta_pdf: str | Path) -> list[list]:
    """Parser v2: REPORTE PROGRAMA OFICIAL (apuestas multilínea, Na PREMIO/CLÁSICO)."""
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    paginas = [(p.extract_text() or "").split("\n") for p in reader.pages]

    headers: list[tuple[int, int, int]] = []
    for pi, lineas in enumerate(paginas):
        for li, l in enumerate(lineas):
            m = PATRON_CARRERA_TELA_REPORTE.match(l.strip())
            if m:
                headers.append((pi, li, int(m.group(1))))

    resultado: list[list] = []
    pending_caballos: set[int] | None = None
    skip_first_seq = False
    caballos_columna = _caballos_por_columna_caballo(ruta_pdf)
    for idx, (start_pi, start_li, num_carrera) in enumerate(headers):
        if idx + 1 < len(headers):
            end_pi, end_li, _ = headers[idx + 1]
        else:
            end_pi = len(paginas) - 1
            end_li = len(paginas[end_pi]) if paginas else 0

        race_lines = _segmento_entre_apuestas(paginas, start_pi, start_li, end_pi, end_li)

        if idx == 0:
            prev_lines = paginas[start_pi][:start_li]
            if start_pi > 0:
                prev_lines = paginas[start_pi - 1] + prev_lines
        else:
            p_pi, p_li, _ = headers[idx - 1]
            prev_lines = _segmento_entre_apuestas(paginas, p_pi, p_li, start_pi, start_li)

        next_lines: list[str] | None = None
        if idx + 1 < len(headers):
            n_pi, n_li, _ = headers[idx + 1]
            if idx + 2 < len(headers):
                nn_pi, nn_li, _ = headers[idx + 2]
            else:
                nn_pi = len(paginas) - 1
                nn_li = len(paginas[nn_pi]) if paginas else 0
            next_lines = _segmento_entre_apuestas(paginas, n_pi, n_li, nn_pi, nn_li)

        num_caballos, pending_caballos, consumio_next = _contar_caballos_tela_reporte(
            prev_lines,
            race_lines,
            pending_caballos,
            next_lines=next_lines,
            skip_first_seq=skip_first_seq,
            prev_preheader=(idx == 0),
        )
        skip_first_seq = consumio_next
        # Preferir columna CABALLO (coordenadas) si hay secuencia válida;
        # si no, fallback al conteo por segmentos. No pisar columna con segmento.
        col = caballos_columna.get(num_carrera, 0)
        if col > 0:
            num_caballos = col

        apuestas_vistas: set[str] = set()
        for linea in _extraer_bloque_apuestas_reporte(race_lines):
            parsed = _parsear_linea_bet_reporte(linea)
            if not parsed:
                continue
            nombre, valor = parsed
            if not valor:
                continue
            if es_apuesta_excluida(nombre):
                continue
            codigo = abreviar_apuesta(normalizar_nombre_apuesta(nombre))
            if not codigo or codigo not in CODIGOS_APUESTA_VALIDOS:
                continue
            if codigo in apuestas_vistas:
                continue
            if codigo in APUESTAS_SIN_COMPARAR_VALOR:
                valor = ""
            resultado.append([num_carrera, num_caballos, codigo, valor])
            apuestas_vistas.add(codigo)

    return resultado


_PATRON_TITULO_TELA = re.compile(
    r"Programa\s+Depurado.*?Reunion\s+(\d+)\s+del\s+(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)
_PATRON_FIN_ENCABEZADO_TELA = re.compile(
    r"^(Premio\b|APUESTAS?\s*:|Carrera\b)",
    re.IGNORECASE,
)

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parsear_info_reunion_tela(texto_pagina: str) -> dict[str, str]:
    """Extrae reunión/fecha/hipódromo del encabezado de tela (no fechas del cuerpo)."""
    reunion = ""
    fecha = ""
    hipodromo = ""
    texto = texto_pagina or ""

    m_titulo = _PATRON_TITULO_TELA.search(texto)
    if m_titulo:
        reunion = m_titulo.group(1)
        fecha = m_titulo.group(2)

    m_reun_rep = PATRON_REUNION_TELA_REPORTE.search(texto)
    if m_reun_rep and not reunion:
        reunion = m_reun_rep.group(1)

    m_fecha_es = re.search(
        r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
        texto,
        re.IGNORECASE,
    )
    if m_fecha_es and not fecha:
        mes = _MESES_ES.get(m_fecha_es.group(2).lower())
        if mes:
            fecha = f"{int(m_fecha_es.group(1)):02d}/{mes:02d}/{m_fecha_es.group(3)}"

    for line in texto.split("\n"):
        s = line.strip()
        if not s:
            continue
        if _PATRON_FIN_ENCABEZADO_TELA.match(s):
            break
        if not reunion:
            m = re.search(r"Reunion\s+(\d+)", s, re.IGNORECASE)
            if m:
                reunion = m.group(1)
        if not fecha:
            d = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", s)
            if d:
                fecha = d.group(1)
        if "Hipodromo" in s or "HIPÓDROMO" in s.upper() or "HIPODROMO" in s.upper():
            hipodromo = s

    if not hipodromo or "PROGRAMA" in hipodromo.upper() or len(hipodromo) > 80:
        m_hip = re.search(r"HIP[OÓ]DROMO\s+DE\s+SAN\s+ISIDRO", texto, re.IGNORECASE)
        if m_hip:
            hipodromo = "Hipódromo de San Isidro"

    return {"reunion": reunion, "fecha": fecha, "hipodromo": hipodromo}


def extraer_info_reunion_tela(ruta_pdf: str | Path) -> dict[str, str]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    texto = reader.pages[0].extract_text() or ""
    return _parsear_info_reunion_tela(texto)


def obtener_apuestas_por_carrera(ruta_pdf: str | Path) -> list[list]:
    """Auto-detecta el formato del PDF y extrae las apuestas."""
    if es_tela_depurada(ruta_pdf):
        return _obtener_apuestas_tela_oficial(ruta_pdf)
    if es_tela_reporte_oficial(ruta_pdf):
        return _obtener_apuestas_tela_reporte_oficial(ruta_pdf)
    return _obtener_apuestas_programa_oficial(ruta_pdf)


def _extraer_pases_de_lineas(
    race_lines: list[str],
    num_carrera: int,
    resultado: dict[int, dict[str, set[str]]],
) -> None:
    pases_carrera: dict[str, set[str]] = {}
    for l in race_lines:
        s = l.strip()
        if not s or s == "CHAQUETILLAS":
            continue
        for m in PATRON_PASE_TELA.finditer(s):
            bet_raw = m.group(1).lower()
            pase_raw = m.group(2)
            pase_norm = _normalizar_pase(pase_raw)
            codigo = abreviar_apuesta(bet_raw)
            if codigo:
                pases_carrera.setdefault(codigo, set()).add(pase_norm)
    if pases_carrera:
        dest = resultado.setdefault(num_carrera, {})
        for codigo, pases_set in pases_carrera.items():
            dest.setdefault(codigo, set()).update(pases_set)


def _extraer_pases_tela_depurada(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    resultado: dict[int, dict[str, set[str]]] = {}

    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        lineas = texto.split("\n")
        if not lineas:
            continue

        apuestas_indices = [
            i for i, l in enumerate(lineas)
            if l.strip().upper().startswith("APUESTAS:")
        ]
        if not apuestas_indices:
            continue

        for idx, start_idx in enumerate(apuestas_indices):
            end_idx = apuestas_indices[idx + 1] if idx + 1 < len(apuestas_indices) else len(lineas)
            race_lines = lineas[start_idx:end_idx]

            num_carrera = None
            for l in race_lines:
                s = l.strip()
                if s.isdigit() and 1 <= int(s) <= 30:
                    num_carrera = int(s)
                    break
            if num_carrera is None:
                for back in range(start_idx - 1, max(start_idx - 15, -1), -1):
                    s = lineas[back].strip()
                    if s.isdigit() and 1 <= int(s) <= 30:
                        num_carrera = int(s)
                        break
            if num_carrera is None:
                continue

            _extraer_pases_de_lineas(race_lines, num_carrera, resultado)

    return resultado


def _extraer_pases_tela_reporte(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    paginas = [(p.extract_text() or "").split("\n") for p in reader.pages]
    resultado: dict[int, dict[str, set[str]]] = {}

    headers: list[tuple[int, int, int]] = []
    for pi, lineas in enumerate(paginas):
        for li, l in enumerate(lineas):
            m = PATRON_CARRERA_TELA_REPORTE.match(l.strip())
            if m:
                headers.append((pi, li, int(m.group(1))))

    for idx, (start_pi, start_li, num_carrera) in enumerate(headers):
        if idx + 1 < len(headers):
            end_pi, end_li, _ = headers[idx + 1]
        else:
            end_pi = len(paginas) - 1
            end_li = len(paginas[end_pi]) if paginas else 0
        race_lines = _segmento_entre_apuestas(paginas, start_pi, start_li, end_pi, end_li)
        bloque = _extraer_bloque_apuestas_reporte(race_lines)
        _extraer_pases_de_lineas(bloque, num_carrera, resultado)

    return resultado


def extraer_pases_tela_oficial(ruta_pdf: str | Path) -> dict[int, dict[str, set[str]]]:
    """Extrae info de pases (1er.Pase, 2do.Pase, etc.) para apuestas pick.
    Retorna {num_carrera: {codigo: {pase_normalizado, ...}}}"""
    if es_tela_reporte_oficial(ruta_pdf):
        return _extraer_pases_tela_reporte(ruta_pdf)
    return _extraer_pases_tela_depurada(ruta_pdf)


def _normalizar_pase(pase: str) -> str:
    """Normaliza nombre de pase a formato consistente.
    1er. Pase  -> 1er.Pase
    1° Pase    -> 1er.Pase
    ultimo pase -> Ultimo Pase
    Útimo Pase  -> Ultimo Pase (variante PDF sin 'l')
    1er.Pase   -> 1er.Pase
    2do .pase  -> 2do.Pase
    2do.pa se  -> 2do.Pase"""
    if PATRON_ULTIMO_PASE.search(pase):
        return "Ultimo Pase"
    m_grado = re.search(r"(\d+)\s*[°ºª\ufffd]", pase)
    if m_grado:
        n = int(m_grado.group(1))
        mapping = {
            1: "1er.Pase", 2: "2do.Pase", 3: "3er.Pase",
            4: "4to.Pase", 5: "5to.Pase", 6: "6to.Pase",
        }
        if n in mapping:
            return mapping[n]
    pase = pase.strip().lower()
    pase = re.sub(r"p\s*a\s*s\s*e", "pase", pase)
    pase = re.sub(r"\s+", " ", pase)
    pase = re.sub(r"\s+(\.)", r"\1", pase)
    pase = re.sub(r"(\.)\s+", r"\1", pase)
    pase = re.sub(r"\bpase\b", "Pase", pase)
    if pase:
        pase = pase[0].upper() + pase[1:]
    return pase


def normalizar_desde_lista_apuestas(apuestas_raw: list[list]) -> dict[int, dict]:
    resultado: dict[int, dict] = {}
    for num_carrera, cantidad_caballos, codigo_apuesta, valor_str in apuestas_raw:
        if num_carrera not in resultado:
            resultado[num_carrera] = {"caballos": cantidad_caballos, "apuestas": {}}
        else:
            resultado[num_carrera]["caballos"] = max(
                resultado[num_carrera]["caballos"], cantidad_caballos
            )
        valor_float = parsear_monto_str(valor_str)
        resultado[num_carrera]["apuestas"][codigo_apuesta] = valor_float
    return resultado


def normalizar_pdf(ruta_pdf: str | Path, apuestas_raw: Optional[list[list]] = None) -> dict[int, dict]:
    if apuestas_raw is None:
        apuestas_raw = obtener_apuestas_por_carrera(ruta_pdf)
    return normalizar_desde_lista_apuestas(apuestas_raw)


# --- Palermo PDF ---

def _mapear_nombre_apuesta_palermo(descripcion: str) -> Optional[str]:
    if not descripcion:
        return None
    texto = descripcion.strip().lower()
    texto = texto.replace("  ", " ")
    if "cuatrifecta" in texto:
        return "CUA"
    if "trifecta" in texto:
        return "TRI"
    if "doble extra" in texto:
        return "DOB"
    if "doble" in texto:
        return "DOB"
    if "5 y 6" in texto or "5y6" in texto or "5 & 6" in texto:
        return "CAD"
    if "pick cuatro" in texto or "pick 4" in texto:
        return "QTN"
    if "pick cinco" in texto or "pick 5" in texto:
        return "QTP"
    if "exacta" in texto:
        return "EXA"
    if "triplo" in texto:
        return "TPL"
    if "imperfecta" in texto:
        return "IMP"
    return None


def _extraer_carreras_palermo(carreras_str: str) -> list[int]:
    texto = carreras_str.upper()
    m_rango = re.search(r"DESDE\s+LA\s+(\d+)\s*[ªº]?\s+HASTA\s+LA\s+(\d+)\s*[ªº]?", texto)
    if m_rango:
        inicio = int(m_rango.group(1))
        fin = int(m_rango.group(2))
        if inicio <= fin:
            return list(range(inicio, fin + 1))
    numeros = re.findall(r"(\d+)\s*[ªº]?", carreras_str)
    return [int(n) for n in numeros]


def leer_palermo_desde_pdf(ruta_pdf: str | Path) -> dict:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf)
    fechas_encontradas: list[str] = []
    apuestas_por_fecha: dict[str, dict[int, dict[str, Optional[float]]]] = {}
    resumen_por_fecha: dict[str, dict[str, dict]] = {}

    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""
        fecha_actual: Optional[str] = None
        for linea in texto.split("\n"):
            linea_stripped = linea.strip()
            if not linea_stripped:
                continue
            for f in PATRON_FECHA.findall(linea_stripped):
                if f not in fechas_encontradas:
                    fechas_encontradas.append(f)
                fecha_actual = f
            if "(" not in linea_stripped or ")" not in linea_stripped:
                continue
            m = PATRON_FILA_PALERMO.match(linea_stripped)
            if not m:
                continue
            if not fecha_actual:
                continue
            descripcion = m.group(1).strip()
            monto_str = m.group(2).strip()
            carreras_str = m.group(3).strip()
            codigo_apuesta = _mapear_nombre_apuesta_palermo(descripcion)
            if not codigo_apuesta:
                continue
            valor = parsear_monto_str(monto_str)
            if valor is None:
                continue
            carreras = _extraer_carreras_palermo(carreras_str)
            if not carreras:
                continue
            if fecha_actual not in apuestas_por_fecha:
                apuestas_por_fecha[fecha_actual] = {}
            if fecha_actual not in resumen_por_fecha:
                resumen_por_fecha[fecha_actual] = {}
            if codigo_apuesta not in resumen_por_fecha[fecha_actual]:
                resumen_por_fecha[fecha_actual][codigo_apuesta] = {
                    "conteo_lineas": 0,
                    "valor": valor,
                    "carreras": set(),
                }
            resumen_por_fecha[fecha_actual][codigo_apuesta]["conteo_lineas"] += 1
            resumen_por_fecha[fecha_actual][codigo_apuesta]["valor"] = valor
            for carrera in carreras:
                if carrera not in apuestas_por_fecha[fecha_actual]:
                    apuestas_por_fecha[fecha_actual][carrera] = {}
                apuestas_por_fecha[fecha_actual][carrera][codigo_apuesta] = valor
                if isinstance(resumen_por_fecha[fecha_actual][codigo_apuesta]["carreras"], set):
                    resumen_por_fecha[fecha_actual][codigo_apuesta]["carreras"].add(carrera)

    return {
        "fechas": fechas_encontradas,
        "apuestas_por_fecha": apuestas_por_fecha,
        "resumen_por_fecha": resumen_por_fecha,
    }


# --- Oficial Palermo PDF ---

def _mapear_apuesta_oficial(nombre: str) -> Optional[str]:
    n = (nombre or "").strip().lower()
    if not n:
        return None
    n = n.split("$", 1)[0].strip()
    if n in {"ganador", "segundo", "tercero"}:
        return None
    n = " ".join(n.split())
    for sufijo in (" acumulado", " corrida", " al reves", " atras"):
        if n.endswith(sufijo):
            n = n[:-len(sufijo)].strip()
            break
    if "doble extra" in n or n == "doble":
        return "DOB"
    if n in {"5 y 6", "5y6", "5 & 6"}:
        return "CAD"
    if n in {"pick 4", "pick cuatro"}:
        return "QTN"
    if n == "triplo":
        return "TPL"
    if n == "exacta":
        return "EXA"
    if n == "trifecta":
        return "TRI"
    if n == "imperfecta":
        return "IMP"
    if n == "cuatrifecta":
        return "CUA"
    return None


def extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial: str | Path) -> list[dict]:
    import pypdf
    reader = pypdf.PdfReader(ruta_pdf_oficial)
    carreras_apuestas: dict[int, set[str]] = {}
    ultima_carrera_detectada: Optional[int] = None

    for page in reader.pages:
        texto = page.extract_text() or ""
        if not texto.strip():
            continue
        lineas = texto.split("\n")
        carreras_en_pagina: list[tuple[int, int]] = []
        apuestas_en_pagina: list[tuple[int, str]] = []

        for idx, linea in enumerate(lineas):
            l = (linea or "").strip()
            if not l:
                continue
            mc = PATRON_CARRERA_OFICIAL.search(l)
            if mc:
                carreras_en_pagina.append((idx, int(mc.group(1))))
            ma = PATRON_APUESTAS_A.search(l)
            if ma:
                apuestas_en_pagina.append((idx, ma.group(1)))

        if not apuestas_en_pagina:
            continue
        if not carreras_en_pagina and ultima_carrera_detectada is not None:
            carreras_en_pagina = [(0, ultima_carrera_detectada + 1)]
        if not carreras_en_pagina:
            continue
        ultima_carrera_detectada = max(n for _, n in carreras_en_pagina)

        for idx_apuesta, listado in apuestas_en_pagina:
            previas = [(i, n) for (i, n) in carreras_en_pagina if i <= idx_apuesta]
            if previas:
                num_carrera = previas[-1][1]
            else:
                num_carrera = carreras_en_pagina[0][1]
            if num_carrera not in carreras_apuestas:
                carreras_apuestas[num_carrera] = set()
            partes = [p.strip() for p in listado.split(",") if p.strip()]
            for p in partes:
                cod = _mapear_apuesta_oficial(p)
                if cod:
                    carreras_apuestas[num_carrera].add(cod)

    resultado = []
    for num_carrera in sorted(carreras_apuestas.keys()):
        resultado.append({
            "carrera": num_carrera,
            "apuestas": sorted(carreras_apuestas[num_carrera]),
        })
    return resultado
