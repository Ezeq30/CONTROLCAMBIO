# -*- coding: utf-8 -*-
"""
Extrae desde un PDF de programa de carreras el número de carrera y el nombre
de la carrera por cada página.

Formato esperado en el PDF: "1ª - Premio NOMBRE - 14:05 hs."
Requiere: pip install pypdf
"""

import re

# Patrón para el título de carrera: "1ª - Premio FLOWING RYE 2013 - 14:05 hs."
# Acepta ª, º o 'a' (por si el PDF devuelve mal el carácter)
_PATRON_CARRERA_PDF = re.compile(
    r"(\d+)\s*[ªºa]\s*[-–]\s*(.+?)\s*[-–]\s*\d{1,2}\s*:\s*\d{2}\s*hs\.?",
    re.IGNORECASE | re.DOTALL,
)


def obtener_carreras_por_pagina(ruta_pdf):
    """
    Lee el PDF y retorna, por cada página, el número de carrera y el nombre
    de la carrera (si la página contiene el encabezado de una carrera).

    Formato esperado en el PDF: "1ª - Premio NOMBRE - 14:05 hs."

    Parámetros
    ----------
    ruta_pdf : str
        Ruta al archivo PDF.

    Retorna
    -------
    list[dict]
        Lista de diccionarios, uno por cada página del PDF. Cada elemento tiene:
        - "pagina": int (número de página, 1-based)
        - "numero_carrera": int o None (número de la carrera si la página la contiene)
        - "nombre_carrera": str o None (nombre de la carrera si la página la contiene)

    Raises
    ------
    ImportError
        Si no está instalada la librería pypdf.
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("Se necesita la librería pypdf. Instalar con: pip install pypdf")

    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []

    for num_pagina in range(len(reader.pages)):
        pagina_actual = num_pagina + 1  # 1-based
        texto = reader.pages[num_pagina].extract_text() or ""

        numero_carrera = None
        nombre_carrera = None

        m = _PATRON_CARRERA_PDF.search(texto)
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


# Patrón para cada apuesta: "Nombre Apuesta $ valor" (valor con dígitos, punto o coma)
_PATRON_APUESTA_VALOR = re.compile(
    r"(.+?)\s*\$\s*([\d.,]+)",
    re.IGNORECASE,
)

# Apuestas a excluir: desde 2do pase en adelante (2do, 3er, 4to, 5to, Ultimo pase, Final)
# Nota: "Final 1er.Pase" (ej. "Cuaterna Final 1er.Pase") debe INCLUIRSE.
_PATRON_EXCLUIR_PASE_SIN_FINAL = re.compile(
    r"2do\.?\s*pase|3er\.?\s*pase|4to\.?\s*pase|5to\.?\s*pase|ultimo\s*pase",
    re.IGNORECASE,
)
_PATRON_FINAL = re.compile(r"\bfinal\b|final\s*pase", re.IGNORECASE)
_PATRON_PRIMER_PASE = re.compile(r"\b1er\.?\s*pase\b|\b1re\.?\s*pase\b", re.IGNORECASE)


def es_apuesta_excluida(nombre):
    """
    Devuelve True si la apuesta debe excluirse (2do pase en adelante, último pase, etc.).
    Regla especial: si contiene 'Final' pero también '1er.Pase' (o '1re.Pase'), NO se excluye.
    'Doble Final Plus' y variantes de Doble se consideran DOB y no se excluyen.
    """
    if not nombre:
        return False
    # Doble Final Plus, Doble Plus, etc. son DOB y no deben excluirse
    if nombre.strip().lower().startswith("doble"):
        return False
    if _PATRON_EXCLUIR_PASE_SIN_FINAL.search(nombre):
        return True
    if _PATRON_FINAL.search(nombre):
        # Permitir "Final 1er.Pase"
        if _PATRON_PRIMER_PASE.search(nombre):
            return False
        return True
    return False


# Mapeo de abreviaturas (debe estar antes de normalizar_nombre_apuesta para que pueda usarlo)
_MAPEO_ABREVIATURAS = {
    "ganador": "GAN",
    "segundo": "SEG",
    "tercero": "TER",
    "exacta": "EXA",
    "trifecta": "TRI",
    "imperfecta": "IMP",
    "cuatrifecta": "CUA",
    "doble": "DOB",
    "triplo": "TPL",
    "cuaterna": "QTN",
    "quintuplo": "QTP",
    "cadena": "CAD",
}

_CODIGOS_APUESTA_VALIDOS = set(_MAPEO_ABREVIATURAS.values())


def normalizar_nombre_apuesta(nombre):
    """
    Simplifica el nombre de la apuesta extrayendo solo la primera palabra
    cuando contiene 'Pase' o cuando la primera palabra está en el diccionario de abreviaturas.
    
    Ejemplos:
    - 'Cadena Con Jackpot 1er.Pase (Única Base)' → 'Cadena'
    - 'Cuaterna 1er.Pase' → 'Cuaterna'
    - 'Quintuplo 1er.Pase' → 'Quintuplo'
    - 'Triplo 1er.Pase' → 'Triplo'
    - 'Doble Plus' → 'Doble'
    - 'Imperfecta Extra' → 'Imperfecta'
    - 'Imperfecta' → 'Imperfecta' (sin cambios)
    """
    nombre = nombre.strip()
    if not nombre:
        return nombre
    
    palabras = nombre.split()
    if not palabras:
        return nombre
    
    primera_palabra = palabras[0]
    
    # Si contiene "Pase" o la primera palabra está en el diccionario de abreviaturas,
    # tomar solo la primera palabra
    if "pase" in nombre.lower() or primera_palabra.lower() in _MAPEO_ABREVIATURAS:
        return primera_palabra
    
    return nombre


def abreviar_apuesta(nombre):
    """
    Convierte el nombre de la apuesta a su abreviatura (case-insensitive).
    Si no hay mapeo, devuelve el nombre tal cual.
    """
    nombre = (nombre or "").strip()
    if not nombre:
        return nombre
    return _MAPEO_ABREVIATURAS.get(nombre.lower(), nombre)


def obtener_caballos_por_carrera(ruta_pdf):
    """
    Extrae del PDF la cantidad de caballos por cada carrera.
    
    Retorna
    -------
    dict[int, int]
        Diccionario {num_carrera: cantidad_caballos}
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("Se necesita la librería pypdf. Instalar con: pip install pypdf")

    reader = pypdf.PdfReader(ruta_pdf)
    resultado = {}

    # Patrón para números de caballo: "01 NOMBRE", "02 NOMBRE", etc.
    patron_caballo = re.compile(r"^(\d{2})\s+[A-Z]", re.MULTILINE | re.IGNORECASE)

    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""

        # Número de carrera de esta página
        m_carrera = _PATRON_CARRERA_PDF.search(texto)
        if not m_carrera:
            continue
        num_carrera = int(m_carrera.group(1))

        # Buscar todos los números de caballo (01, 02, ..., 15, 16, etc.)
        numeros_caballos = set()
        for m in patron_caballo.finditer(texto):
            num = int(m.group(1))
            if 1 <= num <= 24:  # Rango razonable de caballos
                numeros_caballos.add(num)

        # La cantidad es el número más alto encontrado (o el total de números únicos)
        cantidad = max(numeros_caballos) if numeros_caballos else 0
        resultado[num_carrera] = cantidad

    return resultado


def obtener_apuestas_por_carrera(ruta_pdf):
    """
    Extrae del PDF, por cada carrera, todas las apuestas indicadas en la línea
    APUESTAS (y la línea siguiente si existe), con su valor sin el signo $.
    No se incluyen apuestas desde 2do pase en adelante (2do.Pase, 3er.Pase,
    4to.Pase, 5to.Pase, Ultimo Pase, Cuaterna Final, Triplo Final, etc.).
    Sí se incluyen Cadena 1er.Pase y Quintuplo 1er.Pase cuando vienen en la
    misma línea que otras de 2do pase (se toma solo el segmento que lleva el valor).

    Retorna
    -------
    list[list]
        Lista de tuplas [num_carrera, cantidad_caballos, apuesta, valor]. Ejemplo:
        [[1, 15, "GAN", ""],
         [1, 15, "IMP", "1000"],
         [1, 15, "TRI", "1000"],
         [1, 15, "QTN", "2000"],
         [1, 15, "DOB", "1000"], ...]

    Raises
    ------
    ImportError
        Si no está instalada la librería pypdf.
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("Se necesita la librería pypdf. Instalar con: pip install pypdf")

    reader = pypdf.PdfReader(ruta_pdf)
    resultado = []
    
    # Obtener cantidad de caballos por carrera
    caballos_por_carrera = obtener_caballos_por_carrera(ruta_pdf)

    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""

        # Número de carrera de esta página
        m_carrera = _PATRON_CARRERA_PDF.search(texto)
        if not m_carrera:
            continue
        num_carrera = int(m_carrera.group(1))
        cantidad_caballos = caballos_por_carrera.get(num_carrera, 0)

        # Bloque de APUESTAS: la línea que contiene "APUESTAS:" y sus continuaciones.
        # En algunos PDFs, una apuesta y su monto quedan partidos en renglones distintos
        # (ej. "... Doble" en una línea y "$2000" en la siguiente).
        lineas = texto.split("\n")
        bloque_apuestas = []
        patron_linea_apuesta = re.compile(
            r"\$|ganador|segundo|tercero|exacta|trifecta|imperfecta|cuatrifecta|doble|triplo|cuaterna|quintuplo|cadena",
            re.IGNORECASE
        )
        for i, lin in enumerate(lineas):
            if "APUESTAS:" in lin.upper():
                # Quitar el prefijo "APUESTAS:" y tomar esta línea
                idx = lin.upper().index("APUESTAS:")
                linea_inicial = lin[idx + len("APUESTAS:"):].strip()
                if linea_inicial:
                    bloque_apuestas.append(linea_inicial)

                # Incluir líneas siguientes mientras parezcan continuación de apuestas.
                # Esto cubre saltos de línea donde el nombre y el monto quedan separados.
                max_lineas_continuacion = 6
                j = i + 1
                while j < len(lineas) and len(bloque_apuestas) < (1 + max_lineas_continuacion):
                    sig = lineas[j].strip()
                    if not sig:
                        break
                    if not patron_linea_apuesta.search(sig):
                        break
                    bloque_apuestas.append(sig)
                    j += 1
                break

        texto_apuestas = " ".join(bloque_apuestas)
        if not texto_apuestas:
            continue

        # Buscar todos "algo $ número"; excluir apuestas desde 2do pase en adelante.
        # Si hay varias apuestas separadas por coma (ej. "Cuaterna 2do.Pase, Cadena 1er.Pase $200"),
        # el valor corresponde a la última; usamos solo esa para no excluir Cadena/Quintuplo 1er.Pase.
        # Caso especial: "Ganador, Segundo, Tercero $ 2" → queremos ver las tres apuestas.
        for m in _PATRON_APUESTA_VALOR.finditer(texto_apuestas):
            apuesta_bruta = m.group(1).strip().rstrip(",")
            valor = m.group(2).strip()
            if not apuesta_bruta or not valor:
                continue

            # Caso especial: bloque que contiene Ganador / Segundo / Tercero
            # Solo nos interesa saber que existen estas apuestas; el monto no es crítico.
            if "Ganador" in apuesta_bruta:
                partes = [p.strip() for p in apuesta_bruta.split(",") if p.strip()]
                for p in partes:
                    # Para Ganador / Segundo / Tercero no forzamos ningún filtro de pases,
                    # y podemos ignorar el valor (lo dejamos vacío).
                    p_norm = normalizar_nombre_apuesta(p)
                    p_cod = abreviar_apuesta(p_norm)
                    if p_cod in _CODIGOS_APUESTA_VALIDOS:
                        resultado.append([num_carrera, cantidad_caballos, p_cod, ""])
                continue

            # Lógica genérica para el resto de apuestas
            apuesta = apuesta_bruta
            if "," in apuesta:
                # En bloques mixtos, quedarnos solo con el último tramo (el que lleva el valor)
                apuesta = apuesta.rsplit(",", 1)[-1].strip()

            # Excluir desde 2do pase en adelante (permitiendo "Final 1er.Pase")
            if not es_apuesta_excluida(apuesta):
                # Normalizar el nombre (ej. "Cadena Con Jackpot 1er.Pase" → "Cadena")
                apuesta_normalizada = normalizar_nombre_apuesta(apuesta)
                apuesta_cod = abreviar_apuesta(apuesta_normalizada)
                if apuesta_cod in _CODIGOS_APUESTA_VALIDOS:
                    resultado.append([num_carrera, cantidad_caballos, apuesta_cod, valor])

    return resultado


def _parsear_monto_str(valor_str):
    """
    Convierte un string de monto a float, aceptando:
    - Punto como separador de miles: "5.000" -> 5000.0
    - Coma como decimal europeo: "1000,50" -> 1000.5
    - Formato mixto: "1.000,50" -> 1000.5
    Retorna None si no se puede parsear.
    """
    if not valor_str or not isinstance(valor_str, str):
        return None
    s = valor_str.strip()
    if not s:
        return None
    # Formato europeo con coma decimal: 1.000,50 -> quitar puntos, coma a punto
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    # Solo punto(s): "5.000" = 5000 (miles), "5.5" = 5.5 (decimal)
    if "." in s:
        partes = s.split(".")
        # Si la parte tras el último punto tiene exactamente 3 dígitos y todo son dígitos -> miles
        if len(partes) >= 2 and all(p.isdigit() for p in partes) and len(partes[-1]) == 3:
            try:
                return float(s.replace(".", ""))
            except ValueError:
                pass
        try:
            return float(s)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalizar_desde_lista_apuestas(apuestas_raw):
    """
    Construye la estructura normalizada a partir de la lista de apuestas
    [num_carrera, cantidad_caballos, codigo_apuesta, valor].
    """
    resultado = {}
    
    for num_carrera, cantidad_caballos, codigo_apuesta, valor_str in apuestas_raw:
        if num_carrera not in resultado:
            resultado[num_carrera] = {
                "caballos": cantidad_caballos,
                "apuestas": {}
            }
        
        valor_float = _parsear_monto_str(valor_str)
        resultado[num_carrera]["apuestas"][codigo_apuesta] = valor_float
    
    return resultado


def _normalizar_pdf(ruta_pdf, apuestas_raw=None):
    """
    Normaliza los datos extraídos del PDF en una estructura de diccionario.
    Si se pasa apuestas_raw (lista ya leída), no se vuelve a leer el PDF.

    Retorna
    -------
    dict[int, dict]
        Estructura: {num_carrera: {"caballos": int, "apuestas": {codigo: float o None}}}
    """
    if apuestas_raw is None:
        apuestas_raw = obtener_apuestas_por_carrera(ruta_pdf)
    return _normalizar_desde_lista_apuestas(apuestas_raw)


def _normalizar_reporte(ruta_reporte):
    """
    Lee reporte.txt y extrae cantidad de caballos, apuestas activas y valores mínimos.
    
    Retorna
    -------
    dict[int, dict]
        Estructura: {num_carrera: {"caballos": int, "apuestas": {codigo: float o None}}}
    """
    with open(ruta_reporte, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    
    resultado = {}
    
    # 1. Extraer cantidad de caballos y apuestas activas por carrera
    # Patrón para líneas de carrera: "1  GAN SEG TER 1/9 1/9 ..."
    patron_carrera = re.compile(r"^\s*(\d+)\s+([A-Z\s]+?)(?:\s+1/9)+", re.MULTILINE)
    patron_caballos = re.compile(r"1/9")
    patron_scr = re.compile(r"\bSCR\b", re.IGNORECASE)
    patron_apuestas_linea = re.compile(r"\b(GAN|SEG|TER|EXA|TRI|IMP|DOB|TPL|QTN|QTP|CAD|CUA)\b")
    
    lineas = contenido.split("\n")
    apuestas_por_carrera = {}  # {num_carrera: set de códigos}
    caballos_por_carrera = {}  # {num_carrera: cantidad}
    
    # Buscar líneas de carrera y contar caballos
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        m = patron_carrera.match(linea)
        if m:
            num_carrera = int(m.group(1))
            # Contar caballos: cada "1/9" cuenta 1, y cada "SCR" también cuenta 1
            cantidad = len(patron_caballos.findall(linea)) + len(patron_scr.findall(linea))
            caballos_por_carrera[num_carrera] = cantidad
            
            # Extraer apuestas de esta línea
            apuestas_en_linea = set(patron_apuestas_linea.findall(linea))
            if num_carrera not in apuestas_por_carrera:
                apuestas_por_carrera[num_carrera] = set()
            apuestas_por_carrera[num_carrera].update(apuestas_en_linea)
            
            # Buscar líneas siguientes con apuestas adicionales (ej. "DOB( 1,2 )")
            # Las líneas siguientes que empiezan con espacios pertenecen a esta carrera
            j = i + 1
            max_lineas_siguientes = 15  # evita bucles infinitos
            while j < len(lineas) and (j - (i + 1)) < max_lineas_siguientes:
                linea_siguiente = lineas[j]
                linea_stripped = linea_siguiente.strip()
                if not linea_stripped:
                    break
                # Línea indentada (espacio o tab al inicio)
                if not (linea_siguiente.startswith(" ") or linea_siguiente.startswith("\t")):
                    break
                # Otra carrera: empieza con número de carrera
                if re.match(r"^\s*\d+\s+", linea_siguiente):
                    break
                apuestas_adicionales = patron_apuestas_linea.findall(linea_siguiente)
                if apuestas_adicionales:
                    apuestas_por_carrera[num_carrera].update(apuestas_adicionales)
                j += 1
        i += 1
    
    # 2. Extraer valores mínimos desde RSM TABLE
    valores_por_carrera = {}  # {num_carrera: {codigo_apuesta: valor}}
    
    # Buscar sección RSM TABLE
    inicio_rsm = contenido.find("RSM TABLE")
    if inicio_rsm != -1:
        # Leer desde RSM TABLE hasta encontrar una línea vacía seguida de otra sección
        seccion_rsm = contenido[inicio_rsm:]
        # Buscar hasta encontrar "TIM BETTING" o similar
        fin_rsm_1 = seccion_rsm.find("\n\n\n")
        fin_rsm_2 = seccion_rsm.find("TIM BETTING")
        fin_rsm = None
        if fin_rsm_1 != -1 and fin_rsm_2 != -1:
            fin_rsm = min(fin_rsm_1, fin_rsm_2)
        elif fin_rsm_1 != -1:
            fin_rsm = fin_rsm_1
        elif fin_rsm_2 != -1:
            fin_rsm = fin_rsm_2
        
        if fin_rsm is not None and fin_rsm != -1:
            seccion_rsm = seccion_rsm[:fin_rsm]
        
        # Patrón para líneas RSM: "  2  ALL  ---  EXA  TS  1000,00 ..."
        patron_rsm = re.compile(
            r"^\s*\d+\s+([^\s]+(?:[-\s,][^\s]+)*)\s+---\s+([A-Z]+)\s+TS\s+([\d.,]+)",
            re.MULTILINE
        )
        
        # Mapeo de códigos RSM a códigos estándar
        mapeo_rsm = {
            "WPS": None,  # WPS incluye GAN, SEG, TER pero no lo mapeamos directamente
            "EXA": "EXA",
            "TRI": "TRI",
            "IMP": "IMP",
            "DOB": "DOB",
            "TPL": "TPL",
            "QTN": "QTN",
            "QTP": "QTP",
            "CAD": "CAD",
            "CUA": "CUA",
        }
        
        # Carreras "reales" del reporte (las que tienen línea con 1/9). ALL solo aplica a estas.
        carreras_reales_reporte = sorted(caballos_por_carrera.keys()) if caballos_por_carrera else []

        for m in patron_rsm.finditer(seccion_rsm):
            race_map = m.group(1).strip()
            tipo_rsm = m.group(2).strip()
            valor_str = m.group(3).strip()
            
            valor_float = _parsear_monto_str(valor_str)
            if valor_float is None:
                continue
            
            # Mapear tipo
            codigo_apuesta = mapeo_rsm.get(tipo_rsm)
            if not codigo_apuesta:
                continue
            
            # Expandir race_map: si es ALL, solo carreras que existen en el reporte (no los 15 renglones del RSM)
            if race_map.upper() == "ALL":
                carreras = list(carreras_reales_reporte) if carreras_reales_reporte else _expandir_race_map(race_map)
            else:
                carreras = _expandir_race_map(race_map)
            
            # Asignar valor a cada carrera (solo a carreras reales si tenemos lista)
            for carrera in carreras:
                if carreras_reales_reporte and carrera not in carreras_reales_reporte:
                    continue
                if carrera not in valores_por_carrera:
                    valores_por_carrera[carrera] = {}
                valores_por_carrera[carrera][codigo_apuesta] = valor_float
    
    # 3. Leer valores por defecto desde CARD DEFAULT MINIMUMS
    valores_default = {}
    inicio_defaults = contenido.find("CARD DEFAULT MINIMUMS - ARS")
    if inicio_defaults != -1:
        seccion_defaults = contenido[inicio_defaults:inicio_defaults+500]
        patron_default = re.compile(r"(GAN|SEG|TER|EXA|IMP|TRI|DOB|TPL|QTN|QTP|CAD|CUA)\s+([\d.,]+)")
        for m in patron_default.finditer(seccion_defaults):
            codigo = m.group(1)
            valor_str = m.group(2)
            v = _parsear_monto_str(valor_str)
            if v is not None:
                valores_default[codigo] = v
    
    # 4. Combinar todo en estructura final (solo carreras con línea 1/9 en el reporte, no las filas del RSM)
    todas_las_carreras = set(caballos_por_carrera.keys()) | set(apuestas_por_carrera.keys())
    
    for num_carrera in todas_las_carreras:
        resultado[num_carrera] = {
            "caballos": caballos_por_carrera.get(num_carrera, 0),
            "apuestas": {}
        }
        
        # Agregar apuestas con sus valores
        apuestas_carrera = apuestas_por_carrera.get(num_carrera, set())
        valores_carrera = valores_por_carrera.get(num_carrera, {})
        
        for codigo in apuestas_carrera:
            # Solo usar valor si está en RSM TABLE para esta carrera. Si no, NULL (no usar CARD DEFAULT MINIMUMS).
            if codigo in valores_carrera:
                resultado[num_carrera]["apuestas"][codigo] = valores_carrera[codigo]
            else:
                resultado[num_carrera]["apuestas"][codigo] = None
    
    return resultado


def _normalizar_reporte_palermo(ruta_reporte):
    """
    Lee la sección RSM TABLE del reporte de Palermo y construye
    la estructura de valores por carrera.

    IMPORTANTE: Cuando un código tiene race_map ALL en RSM TABLE,
    se expande a todas las carreras (1..max_carrera) para asignar
    el valor por defecto, PERO también se registra en codigos_con_all.
    Esto permite que quien consuma estos datos sepa que la presencia
    del código en todas las carreras es un valor por omisión, no una
    afirmación de que la apuesta existe allí.

    Retorna una tupla:
    - valores_por_carrera: dict[int, dict[str, float]]
      {num_carrera: {codigo_apuesta: valor_float}}
    - codigos_con_all: set[str]
      Conjunto de códigos de apuesta que tenían race_map ALL,
      indicando que son valores por defecto, no afirmaciones de presencia.
    """
    with open(ruta_reporte, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()

    inicio_rsm = contenido.find("RSM TABLE")
    if inicio_rsm == -1:
        return {}, set()

    seccion_rsm = contenido[inicio_rsm:]

    fin_rsm_1 = seccion_rsm.find("\n\n\n")
    fin_rsm_2 = seccion_rsm.find("TIM BETTING")
    fin_rsm = None
    if fin_rsm_1 != -1 and fin_rsm_2 != -1:
        fin_rsm = min(fin_rsm_1, fin_rsm_2)
    elif fin_rsm_1 != -1:
        fin_rsm = fin_rsm_1
    elif fin_rsm_2 != -1:
        fin_rsm = fin_rsm_2

    if fin_rsm is not None and fin_rsm != -1:
        seccion_rsm = seccion_rsm[:fin_rsm]

    patron_rsm = re.compile(
        r"^\s*\d+\s+([^\s]+(?:[-\s,][^\s]+)*)\s+---\s+([A-Z]+)\s+TS\s+([\d.,]+)",
        re.MULTILINE
    )

    mapeo_rsm = {
        "EXA": "EXA", "TRI": "TRI", "IMP": "IMP", "DOB": "DOB",
        "TPL": "TPL", "QTN": "QTN", "QTP": "QTP", "CAD": "CAD", "CUA": "CUA",
    }

    max_carrera = 0
    for m in patron_rsm.finditer(seccion_rsm):
        race_map = m.group(1).strip()
        if race_map.upper() == "ALL":
            continue
        carreras = _expandir_race_map(race_map)
        if carreras:
            max_carrera = max(max_carrera, max(carreras))

    if max_carrera == 0:
        max_carrera = 15

    valores_por_carrera = {}
    codigos_con_all = set()  # Apuestas con race_map ALL: son valores por defecto, no presencia

    for m in patron_rsm.finditer(seccion_rsm):
        race_map = m.group(1).strip()
        tipo_rsm = m.group(2).strip()
        valor_str = m.group(3).strip()

        codigo_apuesta = mapeo_rsm.get(tipo_rsm)
        if not codigo_apuesta:
            continue

        valor_float = _parsear_monto_str(valor_str)
        if valor_float is None:
            continue

        es_all = race_map.upper() == "ALL"
        if es_all:
            carreras = list(range(1, max_carrera + 1))
            codigos_con_all.add(codigo_apuesta)  # Marcar: es valor default, no presencia real
        else:
            carreras = _expandir_race_map(race_map)

        for carrera in carreras:
            if carrera not in valores_por_carrera:
                valores_por_carrera[carrera] = {}
            valores_por_carrera[carrera][codigo_apuesta] = valor_float

    return valores_por_carrera, codigos_con_all


def _expandir_race_map(race_map):
    """
    Expande un race_map del RSM TABLE a lista de números de carrera.
    
    Ejemplos:
    - "ALL" -> [1, 2, 3, ..., 15]
    - "1-13" -> [1, 2, 3, ..., 13]
    - "1,5,7" -> [1, 5, 7]
    - "2,4,6-7,10" -> [2, 4, 6, 7, 10]  (rangos dentro de listas)
    - "14" -> [14]
    """
    race_map = race_map.strip().upper()
    
    if race_map == "ALL":
        # Asumimos máximo 15 carreras (puede ajustarse)
        return list(range(1, 16))
    
    carreras = []
    
    # Primero dividir por comas para manejar listas como "2,4,6-7,10"
    if "," in race_map:
        partes = race_map.split(",")
        for parte in partes:
            parte = parte.strip()
            if not parte:
                continue
            
            # Cada parte puede ser un número único o un rango "X-Y"
            if "-" in parte:
                # Es un rango: "6-7"
                rango_parts = parte.split("-")
                if len(rango_parts) == 2:
                    try:
                        inicio = int(rango_parts[0].strip())
                        fin = int(rango_parts[1].strip())
                        carreras.extend(range(inicio, fin + 1))
                    except ValueError:
                        pass
            else:
                # Es un número único: "2", "4", "10"
                try:
                    carreras.append(int(parte))
                except ValueError:
                    pass
        return carreras
    
    # Si no hay comas, puede ser un rango simple "1-13" o un número único "14"
    if "-" in race_map:
        partes = race_map.split("-")
        if len(partes) == 2:
            try:
                inicio = int(partes[0].strip())
                fin = int(partes[1].strip())
                return list(range(inicio, fin + 1))
            except ValueError:
                pass
    
    # Número único: "14"
    try:
        return [int(race_map)]
    except ValueError:
        return []


def _normalizar_posting_prices(ruta):
    """Extrae valores de la seccion CARD POSTING PRICES de un TXT.
    Estructura identica a RSM TABLE (mismas columnas iniciales),
    con columnas extras (default bet amt, association map) que se ignoran.
    Retorna (valores_por_carrera, codigos_con_all) exactamente como
    _normalizar_reporte_palermo() para compatibilidad ascendente.
    """
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()

    inicio = contenido.find("CARD POSTING PRICES")
    if inicio == -1:
        return {}, set()

    # Extraer solo la seccion CARD POSTING PRICES
    seccion = contenido[inicio:]
    fin_1 = seccion.find("\n\n\n")
    fin_2 = seccion.find("TIM BETTING")
    fin = None
    if fin_1 != -1 and fin_2 != -1:
        fin = min(fin_1, fin_2)
    elif fin_1 != -1:
        fin = fin_1
    elif fin_2 != -1:
        fin = fin_2
    if fin is not None and fin != -1:
        seccion = seccion[:fin]

    # El mismo regex que RSM TABLE — las columnas extra no se capturan
    patron = re.compile(
        r"^\s*\d+\s+([^\s]+(?:[-\s,][^\s]+)*)\s+---\s+([A-Z]+)\s+TS\s+([\d.,]+)",
        re.MULTILINE
    )

    mapeo = {
        "EXA": "EXA", "TRI": "TRI", "IMP": "IMP", "DOB": "DOB",
        "TPL": "TPL", "QTN": "QTN", "QTP": "QTP", "CAD": "CAD", "CUA": "CUA",
    }

    # Primera pasada: determinar max_carrera ignorando entradas ALL
    max_carrera = 0
    for m in patron.finditer(seccion):
        race_map = m.group(1).strip()
        if race_map.upper() == "ALL":
            continue
        carreras = _expandir_race_map(race_map)
        if carreras:
            max_carrera = max(max_carrera, max(carreras))
    if max_carrera == 0:
        max_carrera = 15

    # Segunda pasada: poblar estructura expandiendo ALL a 1..max_carrera
    # y registrando los codigos ALL en codigos_con_all para evitar falsos positivos
    valores_por_carrera = {}
    codigos_con_all = set()
    for m in patron.finditer(seccion):
        race_map = m.group(1).strip()
        tipo = m.group(2).strip()
        valor_str = m.group(3).strip()
        codigo_apuesta = mapeo.get(tipo)
        if not codigo_apuesta:
            continue
        valor_float = _parsear_monto_str(valor_str)
        if valor_float is None:
            continue
        es_all = race_map.upper() == "ALL"
        if es_all:
            carreras = list(range(1, max_carrera + 1))
            codigos_con_all.add(codigo_apuesta)
        else:
            carreras = _expandir_race_map(race_map)
        for carrera in carreras:
            if carrera not in valores_por_carrera:
                valores_por_carrera[carrera] = {}
            valores_por_carrera[carrera][codigo_apuesta] = valor_float

    return valores_por_carrera, codigos_con_all


def _merge_posting_prices(rutas):
    """Mergea 1 o 2 archivos de posting prices.
    El segundo sobrescribe al primero si hay conflicto (mismo codigo/misma carrera).
    codigos_con_all se unifica (union de ambos sets).
    """
    valores_final = {}
    codigos_all_final = set()
    for ruta in rutas:
        valores, codigos_all = _normalizar_posting_prices(ruta)
        for carrera, apuestas in valores.items():
            if carrera not in valores_final:
                valores_final[carrera] = {}
            valores_final[carrera].update(apuestas)  # segundo archivo pisa al primero
        codigos_all_final.update(codigos_all)
    return valores_final, codigos_all_final


def comparar_posting_con_reporte(datos_posting, ruta_reporte):
    """Compara valores de CARD POSTING PRICES contra RSM TABLE del reporte.
    datos_posting = (valores_por_carrera, codigos_con_all) igual que _merge_posting_prices.
    Usa _normalizar_reporte_palermo() para leer el RSM TABLE del reporte.
    Retorna (coincide_todo, diferencias).
    """
    valores_posting, codigos_all_posting = datos_posting
    valores_reporte, codigos_all_reporte = _normalizar_reporte_palermo(ruta_reporte)

    diferencias = []
    todas_las_carreras = set(valores_posting.keys()) | set(valores_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_posting = num_carrera in valores_posting
        tiene_reporte = num_carrera in valores_reporte

        if not tiene_posting:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero no en Posting Prices")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en Posting Prices pero no en reporte")
            continue

        # Comparar presencia de codigos (excluyendo ALL para evitar falsos positivos)
        aps_posting = set(valores_posting[num_carrera].keys())
        aps_reporte = set(valores_reporte[num_carrera].keys())
        solo_en_posting = aps_posting - aps_reporte
        solo_en_reporte = aps_reporte - aps_posting
        solo_en_posting -= codigos_all_posting
        solo_en_reporte -= codigos_all_reporte

        if solo_en_posting:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Posting Prices pero no en reporte: {', '.join(sorted(solo_en_posting))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en Posting Prices: {', '.join(sorted(solo_en_reporte))}"
            )

        # Comparar valores numericos de codigos que existen en ambos lados
        for codigo in sorted(aps_posting & aps_reporte):
            v_p = valores_posting[num_carrera].get(codigo)
            v_r = valores_reporte[num_carrera].get(codigo)
            if v_p is None and v_r is None:
                continue
            if v_p is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} sin monto en Posting Prices pero con valor {v_r} en reporte")
                continue
            if v_r is None:
                diferencias.append(f"Carrera {num_carrera}: {codigo} con monto {v_p} en Posting Prices pero NULL en reporte")
                continue
            if abs(v_p - v_r) > 0.01:
                diferencias.append(f"Carrera {num_carrera}: valor de {codigo} difiere (Posting: {v_p}, Reporte: {v_r})")

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias


def comparar_pdf_y_reporte(ruta_pdf, ruta_reporte, apuestas_raw=None):
    """
    Compara los datos extraídos del PDF con los del archivo reporte.txt.
    
    Compara:
    - Cantidad de caballos por carrera
    - Apuestas disponibles por carrera (incluye GAN, SEG, TER)
    - Valores mínimos de apuestas (donde existan en ambos), excepto GAN, SEG y TER
      (esas tres solo se comprueba que existan; no se comparan sus valores)
    
    Parámetros
    ----------
    ruta_pdf : str
        Ruta al archivo PDF
    ruta_reporte : str
        Ruta al archivo reporte.txt
    apuestas_raw : list, optional
        Si ya tienes la lista de apuestas del PDF (obtener_apuestas_por_carrera),
        pásala aquí para no leer el PDF dos veces.
    
    Retorna
    -------
    tuple[bool, list[str]]
        (coincide_todo, diferencias)
        - coincide_todo: True si todo coincide, False si hay diferencias
        - diferencias: Lista de mensajes detallando las diferencias encontradas,
          incluyendo explícitamente el número de carrera afectada
    """
    datos_pdf = _normalizar_pdf(ruta_pdf, apuestas_raw=apuestas_raw)
    datos_reporte = _normalizar_reporte(ruta_reporte)
    
    # GAN, SEG y TER solo se comparan en existencia, no en valor
    apuestas_sin_comparar_valor = {"GAN", "SEG", "TER"}
    diferencias = []
    todas_las_carreras = set(datos_pdf.keys()) | set(datos_reporte.keys())
    
    for num_carrera in sorted(todas_las_carreras):
        tiene_pdf = num_carrera in datos_pdf
        tiene_reporte = num_carrera in datos_reporte
        
        if not tiene_pdf:
            diferencias.append(f"Carrera {num_carrera}: presente en Reporte pero no en PDF")
            continue
        
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en PDF pero no en Reporte")
            continue
        
        # Comparar cantidad de caballos
        caballos_pdf = datos_pdf[num_carrera]["caballos"]
        caballos_reporte = datos_reporte[num_carrera]["caballos"]
        if caballos_pdf != caballos_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: cantidad de caballos difiere "
                f"(PDF: {caballos_pdf}, Reporte: {caballos_reporte})"
            )
        
        # Comparar apuestas disponibles
        apuestas_pdf = set(datos_pdf[num_carrera]["apuestas"].keys())
        apuestas_reporte = set(datos_reporte[num_carrera]["apuestas"].keys())
        
        solo_en_pdf = apuestas_pdf - apuestas_reporte
        solo_en_reporte = apuestas_reporte - apuestas_pdf
        
        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en PDF pero no en Reporte: {', '.join(sorted(solo_en_pdf))}"
            )
        
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Reporte pero no en PDF: {', '.join(sorted(solo_en_reporte))}"
            )
        
        # Comparar valores de apuestas comunes (GAN, SEG y TER solo se comparan en existencia, no en valor)
        apuestas_comunes = apuestas_pdf & apuestas_reporte
        for codigo in apuestas_comunes:
            if codigo in apuestas_sin_comparar_valor:
                continue
            valor_pdf = datos_pdf[num_carrera]["apuestas"][codigo]
            valor_reporte = datos_reporte[num_carrera]["apuestas"][codigo]
            
            # Solo comparar si ambos tienen valor numérico
            if valor_pdf is not None and valor_reporte is not None:
                # Comparar con tolerancia pequeña para floats
                if abs(valor_pdf - valor_reporte) > 0.01:
                    diferencias.append(
                        f"Carrera {num_carrera}: valor de {codigo} es diferente (PDF: {valor_pdf}, Reporte: {valor_reporte})"
                    )
            elif valor_pdf is not None and valor_reporte is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en el PDF figura {valor_pdf} pero en el reporte NULL"
                )
            elif valor_pdf is None and valor_reporte is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en el reporte figura {valor_reporte} pero en el PDF NULL"
                )
    
    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias


def _mapear_nombre_apuesta_palermo(descripcion):
    """
    Dado el texto de la columna izquierda del PDF de Palermo, devuelve el código de apuesta.
    Mapea, por ejemplo:
    - 'Doble' / 'Doble extra'        -> 'DOB'
    - '5 y 6'                        -> 'CAD'
    - 'pick cuatro'                  -> 'QTN'
    - 'pick cinco'                   -> 'QTP'
    - 'exacta'                       -> 'EXA'
    - 'trifecta'                     -> 'TRI'
    - 'cuatrifecta'                  -> 'CUA'
    - 'triplo'                       -> 'TPL'
    - 'imperfecta'                   -> 'IMP'
    """
    if not descripcion:
        return None

    texto = descripcion.strip().lower()

    # Normalizaciones simples
    texto = texto.replace("  ", " ")

    # Mapeos por substring (del más específico al más genérico).
    # IMPORTANTE: 'cuatrifecta' contiene 'trifecta', por eso se evalúa primero.
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


def _leer_palermo_desde_pdf(ruta_pdf):
    """
    Lee el PDF de Palermo y extrae:
    - Lista de fechas encontradas en el texto (formato dd/mm/aaaa, etc.).
    - Estructura de apuestas por carrera y monto:
      {num_carrera: {codigo_apuesta: valor_float}}

    Se asume un formato con 2 columnas:
    - Izquierda: nombre de la apuesta con el monto entre paréntesis, ej. 'Doble (1000,00)'
    - Derecha: mapa de carreras donde se juega esa apuesta, ej. '1-13' o '1,3,5'
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("Se necesita la librería pypdf. Instalar con: pip install pypdf")

    reader = pypdf.PdfReader(ruta_pdf)

    # Regex para fechas tipo 01/02/2026 o 1/2/26
    patron_fecha = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")

    # Regex genérico para fila: "<descripcion>($ monto)  columnas_derecha"
    # Ejemplo de línea: "CUATRIFECTA: ($ 500.-) 2ª4ª6ª9ª; 12ª"
    # Capturamos solo el número dentro de los paréntesis, ignorando el signo $ y el sufijo ".-".
    patron_fila = re.compile(r"(.+?)\(\s*[\$\s]*([\d.,]+)(?:\.-)?\s*\)\s+(.+)")

    fechas_encontradas = []
    # Estructura: {fecha: {carrera: {codigo_apuesta: valor}}}
    apuestas_por_fecha = {}
    # Metadatos para poder aplicar reglas tipo "si aparece una sola vez, es ALL"
    # Estructura: {fecha: {codigo_apuesta: {"conteo_lineas": int, "valor": float, "carreras": set[int]}}}
    resumen_por_fecha = {}

    def _extraer_carreras_palermo(carreras_str):
        """
        Extrae números de carrera desde el texto de la columna derecha.

        Casos soportados:
        - '2ª4ª6ª9ª; 12ª'        -> [2, 4, 6, 9, 12]
        - '1ª, 10ª'             -> [1, 10]
        - 'DESDE LA 1ª HASTA LA 11ª' -> [1, 2, ..., 11]
        """
        texto = carreras_str.upper()

        # Caso especial: 'DESDE LA Xª HASTA LA Yª' -> rango X..Y
        m_rango = re.search(r"DESDE\s+LA\s+(\d+)\s*[ªº]?\s+HASTA\s+LA\s+(\d+)\s*[ªº]?", texto)
        if m_rango:
            inicio = int(m_rango.group(1))
            fin = int(m_rango.group(2))
            if inicio <= fin:
                return list(range(inicio, fin + 1))

        # Caso general: lista de números con o sin sufijo ª / º
        numeros = re.findall(r"(\d+)\s*[ªº]?", carreras_str)
        return [int(n) for n in numeros]

    for num_pagina in range(len(reader.pages)):
        texto = reader.pages[num_pagina].extract_text() or ""

        # Recorremos línea a línea, manteniendo la "fecha actual"
        fecha_actual = None

        for linea in texto.split("\n"):
            linea_stripped = linea.strip()
            if not linea_stripped:
                continue

            # Actualizar fecha actual si la línea contiene alguna fecha
            for f in patron_fecha.findall(linea_stripped):
                if f not in fechas_encontradas:
                    fechas_encontradas.append(f)
                fecha_actual = f

            # Filas de apuestas requieren paréntesis con monto
            if "(" not in linea_stripped or ")" not in linea_stripped:
                continue

            m = patron_fila.match(linea_stripped)
            if not m:
                continue

            # Si todavía no vimos ninguna fecha, no sabemos a qué fecha asociar esta línea
            if not fecha_actual:
                continue

            descripcion = m.group(1).strip()
            monto_str = m.group(2).strip()
            carreras_str = m.group(3).strip()

            codigo_apuesta = _mapear_nombre_apuesta_palermo(descripcion)
            if not codigo_apuesta:
                continue

            valor = _parsear_monto_str(monto_str)
            if valor is None:
                continue

            # Extraer carreras específicas para Palermo (ej. '2ª4ª6ª9ª; 12ª')
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
            # Incrementar el conteo de líneas donde aparece la apuesta en esta fecha
            resumen_por_fecha[fecha_actual][codigo_apuesta]["conteo_lineas"] += 1
            resumen_por_fecha[fecha_actual][codigo_apuesta]["valor"] = valor

            for carrera in carreras:
                if carrera not in apuestas_por_fecha[fecha_actual]:
                    apuestas_por_fecha[fecha_actual][carrera] = {}
                apuestas_por_fecha[fecha_actual][carrera][codigo_apuesta] = valor
                resumen_por_fecha[fecha_actual][codigo_apuesta]["carreras"].add(carrera)

    return {
        "fechas": fechas_encontradas,
        "apuestas_por_fecha": apuestas_por_fecha,
        "resumen_por_fecha": resumen_por_fecha,
    }


def comparar_palermo(ruta_pdf_palermo, ruta_reporte, fecha_objetivo=None, datos_pdf=None):
    """
    Compara, para PALERMO, solo:
    - Apuestas por carrera
    - Montos mínimos de cada apuesta

    Usa:
    - PDF de Palermo (columna izquierda: apuesta y monto; columna derecha: carreras)
    - El mismo reporte.txt utilizado para San Isidro.

    Retorna:
    - coincide_todo: bool
    - diferencias: lista de strings con las diferencias encontradas
    - fechas: lista de fechas detectadas en el PDF de Palermo
    """
    if datos_pdf is None:
        datos_pdf = _leer_palermo_desde_pdf(ruta_pdf_palermo)

    fechas = datos_pdf["fechas"]
    apuestas_por_fecha = datos_pdf["apuestas_por_fecha"]  # {fecha: {carrera: {codigo: valor}}}
    resumen_por_fecha = datos_pdf.get("resumen_por_fecha", {})

    # Si no se indica fecha, usar todas combinadas (fallback seguro)
    # IMPORTANTE: trabajar siempre con copias para no mutar datos_pdf original.
    if fecha_objetivo is None:
        apuestas_pdf = {}
        for _, apuestas_carreras in apuestas_por_fecha.items():
            for carrera, apuestas in apuestas_carreras.items():
                if carrera not in apuestas_pdf:
                    apuestas_pdf[carrera] = {}
                apuestas_pdf[carrera].update(dict(apuestas))
    else:
        apuestas_pdf = {
            carrera: dict(apuestas)
            for carrera, apuestas in apuestas_por_fecha.get(fecha_objetivo, {}).items()
        }

    # Para Palermo usamos un normalizador propio que solo mira RSM TABLE
    # Ignoramos codigos_con_all porque acá comparamos valores reales del reporte
    datos_reporte, _ = _normalizar_reporte_palermo(ruta_reporte)  # {carrera: {codigo_apuesta: valor}}

    # Regla Palermo:
    # Si una apuesta (por ejemplo EXACTA/TRIFECTA) aparece UNA sola vez en el PDF para esa fecha,
    # se interpreta como "misma base para todas las carreras" (equivalente a ALL en el reporte).
    # Entonces expandimos esa apuesta a todas las carreras del reporte con el mismo valor.
    if fecha_objetivo is not None:
        resumen_fecha = resumen_por_fecha.get(fecha_objetivo, {})
        codigos_all_si_unica = {"EXA", "TRI"}
        for codigo in codigos_all_si_unica:
            info = resumen_fecha.get(codigo)
            if not info:
                continue
            if info.get("conteo_lineas", 0) != 1:
                continue
            valor = info.get("valor")
            if valor is None:
                continue
            for carrera in datos_reporte.keys():
                if carrera not in apuestas_pdf:
                    apuestas_pdf[carrera] = {}
                # Solo completar si no estaba explícitamente en el PDF para esa carrera
                if codigo not in apuestas_pdf[carrera]:
                    apuestas_pdf[carrera][codigo] = valor

    diferencias = []
    todas_las_carreras = set(apuestas_pdf.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_pdf = num_carrera in apuestas_pdf
        tiene_reporte = num_carrera in datos_reporte

        if not tiene_pdf:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero sin apuestas en PDF de Palermo")
            continue

        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en PDF de Palermo pero no en reporte")
            continue

        apuestas_carrera_pdf = apuestas_pdf[num_carrera]
        apuestas_carrera_rep = datos_reporte[num_carrera]

        codigos_pdf = set(apuestas_carrera_pdf.keys())
        codigos_rep = set(apuestas_carrera_rep.keys())

        solo_en_pdf = codigos_pdf - codigos_rep
        solo_en_reporte = codigos_rep - codigos_pdf

        if solo_en_pdf:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en PDF de Palermo pero no en reporte: {', '.join(sorted(solo_en_pdf))}"
            )

        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en PDF de Palermo: {', '.join(sorted(solo_en_reporte))}"
            )

        # Comparar montos de apuestas comunes
        codigos_comunes = codigos_pdf & codigos_rep
        for codigo in codigos_comunes:
            valor_pdf = apuestas_carrera_pdf.get(codigo)
            valor_rep = apuestas_carrera_rep.get(codigo)

            if valor_pdf is None and valor_rep is None:
                continue
            if valor_pdf is None and valor_rep is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} sin monto en PDF de Palermo pero con valor {valor_rep} en reporte"
                )
                continue
            if valor_pdf is not None and valor_rep is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} con monto {valor_pdf} en PDF de Palermo pero NULL en reporte"
                )
                continue

            # Ambos tienen valor numérico
            if abs(valor_pdf - valor_rep) > 0.01:
                diferencias.append(
                    f"Carrera {num_carrera}: monto de {codigo} difiere (PDF Palermo: {valor_pdf}, Reporte: {valor_rep})"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias, fechas


def _extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial):
    """
    Lee el PDF oficial y extrae por carrera las apuestas listadas en "APUESTAS A ...".

    Reglas:
    - Ignorar GANADOR, SEGUNDO y TERCERO.
    - Mapear nombres a códigos:
      DOBLE / DOBLE EXTRA -> DOB
      5 Y 6              -> CAD
      PICK 4 / PICK CUATRO -> QTN
      TRIPLO             -> TPL
      EXACTA             -> EXA
      TRIFECTA           -> TRI
      IMPERFECTA         -> IMP
      CUATRIFECTA        -> CUA

    Retorna:
      list[dict] con elementos:
      {"carrera": int, "apuestas": list[str]}
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("Se necesita la librería pypdf. Instalar con: pip install pypdf")

    def _mapear_apuesta_oficial(nombre):
        n = (nombre or "").strip().lower()
        if not n:
            return None
        # En algunos PDFs la línea trae montos mezclados al final (ej. "cuatrifecta $ 10.000.000")
        n = n.split("$", 1)[0].strip()
        # Ignorar estas apuestas
        if n in {"ganador", "segundo", "tercero"}:
            return None
        # Normalizaciones
        n = " ".join(n.split())
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

    reader = pypdf.PdfReader(ruta_pdf_oficial)
    carreras_apuestas = {}  # {num_carrera: set(codigos)}

    # Acepta variantes como "1ª Carrera", "2 ª Carrera", etc.
    # Solo encabezados de carrera al inicio de línea (evita falsos positivos como "1ª y 5ª carrera")
    # El PDF a veces devuelve un carácter extraño entre número y "Carrera" (ej. "3 � Carrera"),
    # por eso aceptamos un separador no alfanumérico opcional.
    patron_carrera = re.compile(r"^\s*(\d+)\s*[^0-9A-Za-z]?\s*Carrera\b", re.IGNORECASE)
    patron_apuestas_a = re.compile(r"APUESTAS?\s+A\s*:?\s+(.+)", re.IGNORECASE)

    # Nota: la extracción de texto del PDF a veces mezcla órdenes.
    # Asignamos cada línea "APUESTAS A ..." a la carrera más cercana en esa página.
    ultima_carrera_detectada = None
    for page in reader.pages:
        texto = page.extract_text() or ""
        if not texto.strip():
            continue

        lineas = texto.split("\n")
        carreras_en_pagina = []  # [(idx_linea, num_carrera)]
        apuestas_en_pagina = []  # [(idx_linea, listado_apuestas)]

        for idx, linea in enumerate(lineas):
            l = (linea or "").strip()
            if not l:
                continue
            mc = patron_carrera.search(l)
            if mc:
                carreras_en_pagina.append((idx, int(mc.group(1))))
            ma = patron_apuestas_a.search(l)
            if ma:
                apuestas_en_pagina.append((idx, ma.group(1)))

        if not apuestas_en_pagina:
            continue

        # Fallback: si esta página no trae encabezado de carrera por error de extracción,
        # asumimos la siguiente carrera respecto de la última detectada.
        if not carreras_en_pagina and ultima_carrera_detectada is not None:
            carreras_en_pagina = [(0, ultima_carrera_detectada + 1)]
        if not carreras_en_pagina:
            continue

        ultima_carrera_detectada = max(n for _, n in carreras_en_pagina)

        for idx_apuesta, listado in apuestas_en_pagina:
            # Buscar carrera previa más cercana; si no hay previa, tomar la primera de la página.
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


def comparar_oficial_palermo_con_reporte(apuestas_oficial, ruta_reporte, apuestas_referencia_pdf=None):
    """
    Compara OFICIAL vs REPORTE para Palermo, solo en apuestas por carrera (sin montos).

    Parámetros
    ----------
    apuestas_oficial : list[dict]
        Salida de _extraer_apuestas_desde_oficial_palermo:
        [{"carrera": int, "apuestas": list[str]}, ...]
    ruta_reporte : str
        Ruta al reporte TXT.

    Retorna
    -------
    tuple[bool, list[str]]
        (coincide_todo, diferencias)
    """
    # Obtener valores del reporte + conjunto de códigos con race_map ALL
    datos_reporte, codigos_con_all = _normalizar_reporte_palermo(ruta_reporte)

    oficial_por_carrera = {}
    for item in apuestas_oficial or []:
        c = int(item.get("carrera"))
        oficial_por_carrera[c] = set(item.get("apuestas") or [])

    diferencias = []
    todas_las_carreras = set(oficial_por_carrera.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_oficial = num_carrera in oficial_por_carrera
        tiene_reporte = num_carrera in datos_reporte

        if not tiene_oficial:
            diferencias.append(f"Carrera {num_carrera}: presente en reporte pero no en oficial")
            continue
        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en oficial pero no en reporte")
            continue

        aps_oficial = oficial_por_carrera[num_carrera]
        aps_reporte = set(datos_reporte[num_carrera].keys())

        solo_en_oficial = aps_oficial - aps_reporte
        solo_en_reporte = aps_reporte - aps_oficial
        # Excluir apuestas con ALL porque su presencia en todas las carreras
        # es un valor por defecto ("EXA=1000 donde exista EXA"), no una
        # afirmación real de que la apuesta está disponible en esa carrera.
        # Si no se excluyeran, darían falsos positivos (ej. Carrera 7: EXA).
        solo_en_reporte -= codigos_con_all

        if solo_en_oficial:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en oficial pero no en reporte: {', '.join(sorted(solo_en_oficial))}"
            )
        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en reporte pero no en oficial: {', '.join(sorted(solo_en_reporte))}"
            )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias


def _mapear_apuesta_planilla(nombre):
    """Mapea nombres de apuestas de planilla La Plata a codigos RSM.

    En La Plata: CUATERNA = QTN (no CUA como en otros hipodromos).
    CUATRIFECTA = CUA.
    """
    if not nombre:
        return None
    texto = nombre.strip().upper()
    if "CUATRIFECTA SUPER" in texto:
        return "CUA"
    if "CUATRIFECTA" in texto:
        return "CUA"
    if "CUATERNA EXTRAORDINARIA" in texto or "CUATERNA EXT" in texto:
        return "QTN"
    if "CUATERNA" in texto:
        return "QTN"
    if "TRIPLO EXTRAORDINARIO" in texto or "TRIPLO EXTRA" in texto:
        return "TPL"
    if "TRIPLO" in texto:
        return "TPL"
    if "TRIFECTA" in texto:
        return "TRI"
    if "IMPERFECTA ESPECIAL" in texto or "IMPERFECTA ESP" in texto:
        return "IMP"
    if "IMPERFECTA" in texto:
        return "IMP"
    if "EXACTA" in texto:
        return "EXA"
    if "DOBLE DESQUITE" in texto or "DOBLE DESQ" in texto:
        return "DOB"
    if "DOBLE" in texto:
        return "DOB"
    if "QUINTUPLO" in texto:
        return "QTP"
    if "CADENA" in texto:
        return "CAD"
    return None


def _leer_planilla_laplata(ruta):
    """Lee planilla XLS de La Plata y extrae caballos y apuestas por carrera.

    Formato esperado:
      Header: MAN  CAR  APUESTA  BASE  APUESTA  BASE  APUESTA  BASE  APUESTA  BASE
      Data:   N    1ª   NOMBRE   $BASE NOMBRE   $BASE ...

    Retorna {num_carrera: dict} con keys "caballos" (int) y "apuestas" ({codigo: float}).
    """
    import xlrd
    wb = xlrd.open_workbook(ruta, formatting_info=False)
    sheet = wb.sheet_by_index(0)

    header_row = None
    man_idx = -1
    car_idx = -1
    for row in range(min(sheet.nrows, 200)):
        values = [str(sheet.cell_value(row, c)).strip().upper() for c in range(sheet.ncols)]
        for c, v in enumerate(values):
            if v == "MAN":
                man_idx = c
            if v == "CAR":
                car_idx = c
        if man_idx >= 0 and car_idx >= 0:
            header_row = row
            break

    if header_row is None:
        return {}

    resultado = {}
    for row in range(header_row + 1, sheet.nrows):
        man_val = str(sheet.cell_value(row, man_idx)).strip()
        car_val = str(sheet.cell_value(row, car_idx)).strip()

        if not man_val or not car_val:
            continue

        m_car = re.match(r"(\d+)\s*[ªº]", car_val)
        if not m_car:
            continue

        num_carrera = int(m_car.group(1))
        try:
            caballos = int(float(man_val))
        except (ValueError, TypeError):
            continue

        apuestas = {}
        bet_start = max(man_idx, car_idx) + 1
        for col in range(bet_start, sheet.ncols - 1, 2):
            if col + 1 >= sheet.ncols:
                break
            bet_name = str(sheet.cell_value(row, col)).strip()
            base_str = str(sheet.cell_value(row, col + 1)).strip()
            if not bet_name:
                continue
            codigo = _mapear_apuesta_planilla(bet_name)
            if codigo is None:
                continue
            valor = _parsear_monto_str(base_str.replace("$", "").strip())
            apuestas[codigo] = valor

        resultado[num_carrera] = {
            "caballos": caballos,
            "apuestas": apuestas
        }

    return resultado


def _normalizar_planilla_laplata(ruta):
    """Wrapper que normaliza planilla La Plata a formato estandar."""
    return _leer_planilla_laplata(ruta)


def comparar_planilla_con_reporte(ruta_xls, ruta_reporte):
    """Compara planilla La Plata (XLS) vs reporte TXT.

    Retorna (coincide_todo, diferencias).

    Nota: GAN, SEG, TER siempre existen en el reporte pero
    no vienen en la planilla. QTN aparece en el reporte como
    valor por defecto cuando no hay CUA en la planilla.
    Se ignoran en la comparacion para evitar falsos positivos.
    """
    datos_planilla = _normalizar_planilla_laplata(ruta_xls)
    datos_reporte = _normalizar_reporte(ruta_reporte)

    if not datos_planilla:
        return False, ["No se pudo leer la planilla o no contiene datos validos"]
    if not datos_reporte:
        return False, ["No se pudo leer el reporte o no contiene datos validos"]

    apuestas_a_ignorar_en_reporte = {"GAN", "SEG", "TER", "QTN"}
    diferencias = []
    todas_las_carreras = set(datos_planilla.keys()) | set(datos_reporte.keys())

    for num_carrera in sorted(todas_las_carreras):
        tiene_planilla = num_carrera in datos_planilla
        tiene_reporte = num_carrera in datos_reporte

        if not tiene_planilla:
            diferencias.append(f"Carrera {num_carrera}: presente en Reporte pero no en Planilla")
            continue

        if not tiene_reporte:
            diferencias.append(f"Carrera {num_carrera}: presente en Planilla pero no en Reporte")
            continue

        caballos_planilla = datos_planilla[num_carrera]["caballos"]
        caballos_reporte = datos_reporte[num_carrera]["caballos"]
        if caballos_planilla != caballos_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: cantidad de caballos difiere "
                f"(Planilla: {caballos_planilla}, Reporte: {caballos_reporte})"
            )

        apuestas_planilla = set(datos_planilla[num_carrera]["apuestas"].keys())
        apuestas_reporte = set(datos_reporte[num_carrera]["apuestas"].keys())

        solo_en_planilla = apuestas_planilla - apuestas_reporte
        solo_en_reporte = (apuestas_reporte - apuestas_planilla) - apuestas_a_ignorar_en_reporte

        if solo_en_planilla:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Planilla pero no en Reporte: {', '.join(sorted(solo_en_planilla))}"
            )

        if solo_en_reporte:
            diferencias.append(
                f"Carrera {num_carrera}: apuestas presentes en Reporte pero no en Planilla: {', '.join(sorted(solo_en_reporte))}"
            )

        apuestas_comunes = apuestas_planilla & apuestas_reporte
        for codigo in apuestas_comunes:
            if codigo in apuestas_a_ignorar_en_reporte:
                continue
            valor_planilla = datos_planilla[num_carrera]["apuestas"][codigo]
            valor_reporte = datos_reporte[num_carrera]["apuestas"][codigo]

            if valor_planilla is not None and valor_reporte is not None:
                if abs(valor_planilla - valor_reporte) > 0.01:
                    diferencias.append(
                        f"Carrera {num_carrera}: valor de {codigo} es diferente (Planilla: {valor_planilla}, Reporte: {valor_reporte})"
                    )
            elif valor_planilla is not None and valor_reporte is None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en Planilla figura {valor_planilla} pero en Reporte NULL"
                )
            elif valor_planilla is None and valor_reporte is not None:
                diferencias.append(
                    f"Carrera {num_carrera}: {codigo} en Reporte figura {valor_reporte} pero en Planilla NULL"
                )

    coincide_todo = len(diferencias) == 0
    return coincide_todo, diferencias


class AgenteComparacion:
    """
    Agente de alto nivel para ejecutar comparaciones del dominio hípico.

    Este agente encapsula los flujos principales del script para permitir
    integrarlo desde otros módulos sin depender del menú interactivo.
    """

    def comparar_san_isidro(self, ruta_pdf, ruta_reporte):
        """
        Ejecuta el flujo completo de San Isidro.

        Retorna un diccionario con:
        - coincide: bool
        - diferencias: list[str]
        - datos_pdf: dict normalizado
        - datos_reporte: dict normalizado
        """
        apuestas = obtener_apuestas_por_carrera(ruta_pdf)
        coincide, diferencias = comparar_pdf_y_reporte(
            ruta_pdf,
            ruta_reporte,
            apuestas_raw=apuestas,
        )
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "datos_pdf": _normalizar_pdf(ruta_pdf, apuestas_raw=apuestas),
            "datos_reporte": _normalizar_reporte(ruta_reporte),
        }

    def comparar_palermo(self, ruta_pdf_palermo, ruta_reporte, fecha_objetivo=None):
        """
        Ejecuta el flujo Palermo (bases/apuestas PDF vs reporte).

        Retorna un diccionario con:
        - coincide: bool
        - diferencias: list[str]
        - fechas_detectadas: list[str]
        - fecha_usada: str|None
        """
        datos_pdf = _leer_palermo_desde_pdf(ruta_pdf_palermo)
        fechas = datos_pdf.get("fechas", [])

        fecha_usada = fecha_objetivo
        if fecha_usada is None and len(fechas) == 1:
            fecha_usada = fechas[0]

        coincide, diferencias, fechas_detectadas = comparar_palermo(
            ruta_pdf_palermo,
            ruta_reporte,
            fecha_objetivo=fecha_usada,
            datos_pdf=datos_pdf,
        )
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "fechas_detectadas": fechas_detectadas,
            "fecha_usada": fecha_usada,
        }

    def comparar_palermo_con_oficial(
        self,
        ruta_pdf_palermo,
        ruta_reporte,
        ruta_pdf_oficial,
        fecha_objetivo=None,
    ):
        """
        Ejecuta comparación Palermo completa:
        - PDF bases/apuestas vs reporte (apuestas y montos)
        - Oficial vs reporte (solo presencia de apuestas)

        Retorna un diccionario con dos bloques:
        - palermo_vs_reporte
        - oficial_vs_reporte
        """
        datos_pdf = _leer_palermo_desde_pdf(ruta_pdf_palermo)
        fechas = datos_pdf.get("fechas", [])

        fecha_usada = fecha_objetivo
        if fecha_usada is None and len(fechas) == 1:
            fecha_usada = fechas[0]

        coincide_pal, diferencias_pal, _ = comparar_palermo(
            ruta_pdf_palermo,
            ruta_reporte,
            fecha_objetivo=fecha_usada,
            datos_pdf=datos_pdf,
        )

        apuestas_oficial = _extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial)
        apuestas_pdf_ref = datos_pdf.get("apuestas_por_fecha", {}).get(fecha_usada, {})
        coincide_oficial, diferencias_oficial = comparar_oficial_palermo_con_reporte(
            apuestas_oficial,
            ruta_reporte,
            apuestas_referencia_pdf=apuestas_pdf_ref,
        )

        return {
            "palermo_vs_reporte": {
                "coincide": coincide_pal,
                "diferencias": diferencias_pal,
                "fechas_detectadas": fechas,
                "fecha_usada": fecha_usada,
            },
            "oficial_vs_reporte": {
                "coincide": coincide_oficial,
                "diferencias": diferencias_oficial,
                "apuestas_oficial": apuestas_oficial,
            },
        }

    def comparar_posting(self, rutas_posting, ruta_reporte):
        """Compara Posting Prices contra el reporte.
        rutas_posting: list[str] de 1 o 2 archivos TXT.
        Retorna dict con coincide, diferencias, datos_posting(tuple).
        """
        datos_posting = _merge_posting_prices(rutas_posting)
        coincide, diferencias = comparar_posting_con_reporte(datos_posting, ruta_reporte)
        return {"coincide": coincide, "diferencias": diferencias, "datos_posting": datos_posting}

    def comparar_laplata(self, ruta_xls, ruta_reporte):
        """Compara planilla La Plata (XLS) vs reporte TXT.
        Retorna dict con coincide, diferencias, datos_planilla, datos_reporte.
        """
        coincide, diferencias = comparar_planilla_con_reporte(ruta_xls, ruta_reporte)
        return {
            "coincide": coincide,
            "diferencias": diferencias,
            "datos_planilla": _normalizar_planilla_laplata(ruta_xls),
            "datos_reporte": _normalizar_reporte(ruta_reporte),
        }


if __name__ == "__main__":
    import os
    import sys
    try:
        import tkinter as _tk
        from tkinter import filedialog as _filedialog
        _TIENE_TK = True
    except Exception:
        _TIENE_TK = False
    _agente = AgenteComparacion()

    def _limpiar_pantalla():
        """
        Limpia la consola para que los menús se vean como una sola pantalla.
        En Windows usa 'cls' y en otros sistemas 'clear'.
        """
        try:
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")
        except Exception:
            # Si por algún motivo falla, simplemente no limpia.
            pass

    def _pedir_ruta(mensaje, extensiones_validas):
        """
        Pide una ruta por consola y valida que exista y tenga una extensión permitida.
        extensiones_validas: conjunto de strings, por ejemplo {'.pdf'} o {'.txt'}.
        """
        while True:
            ruta = input(mensaje).strip().strip('"')
            if not ruta:
                print("Operación cancelada.\n")
                return None

            if not os.path.isfile(ruta):
                print("La ruta ingresada no es un archivo válido. Intente nuevamente.\n")
                continue

            ext = os.path.splitext(ruta)[1].lower()
            if extensiones_validas and ext not in extensiones_validas:
                print(f"Extensión inválida ({ext}). Se esperan archivos de tipo: {', '.join(sorted(extensiones_validas))}\n")
                continue

            return ruta

    def _seleccionar_archivo_gui(extensiones_validas, descripcion):
        """
        Abre un cuadro de diálogo gráfico para seleccionar un archivo.
        extensiones_validas: conjunto de strings como {'.pdf'} o {'.txt'}.
        descripcion: texto descriptivo para el diálogo (por ejemplo 'programa oficial (PDF)').
        """
        if not _TIENE_TK:
            return None

        raiz = _tk.Tk()
        raiz.withdraw()

        patrones = []
        for ext in sorted(extensiones_validas):
            patron = f"*{ext}"
            patrones.append((f"Archivos {ext.upper()}", patron))
        patrones.append(("Todos los archivos", "*.*"))

        ruta = _filedialog.askopenfilename(
            title=f"Seleccionar {descripcion}",
            filetypes=patrones,
        )

        raiz.destroy()

        if not ruta:
            return None

        if not os.path.isfile(ruta):
            return None

        ext = os.path.splitext(ruta)[1].lower()
        if extensiones_validas and ext not in extensiones_validas:
            return None

        return ruta

    def _formatear_apuestas(apuestas_dict):
        """
        Devuelve un string legible de un dict {codigo_apuesta: valor_float_o_None}.
        Ejemplo: {'GAN': None, 'IMP': 1000.0} -> 'GAN, IMP=1000'
        """
        if not apuestas_dict:
            return "-"

        # Orden lógico de códigos para que se vea prolijo
        orden_preferido = ["GAN", "SEG", "TER", "EXA", "IMP", "TRI", "DOB", "TPL", "QTN", "QTP", "CAD", "CUA"]

        def _clave_orden(cod):
            try:
                return (0, orden_preferido.index(cod))
            except ValueError:
                return (1, cod)

        partes = []
        for codigo in sorted(apuestas_dict.keys(), key=_clave_orden):
            valor = apuestas_dict[codigo]
            if valor is None:
                partes.append(f"{codigo}")
            else:
                # Mostrar enteros sin decimales cuando aplique
                if isinstance(valor, (int, float)) and abs(valor - int(valor)) < 1e-6:
                    partes.append(f"{codigo}={int(valor)}")
                else:
                    partes.append(f"{codigo}={valor:.2f}")
        return ", ".join(partes)

    def _imprimir_tabla_san_isidro(datos_pdf_norm, datos_rep_norm):
        """
        Imprime la tabla comparativa PDF vs REPORTE para San Isidro.
        """
        todas_carreras = sorted(set(datos_pdf_norm.keys()) | set(datos_rep_norm.keys()))

        print("")
        print("  DATOS OBTENIDOS DEL PDF")
        print("  " + "-" * 62)
        print("  Carrera  | Cab.   | Apuestas / Montos")
        print("  ---------+--------+----------------------------------------")
        for c in todas_carreras:
            info = datos_pdf_norm.get(c)
            cab = info.get("caballos", 0) if info else 0
            ap = _formatear_apuestas(info.get("apuestas", {})) if info else "-"
            print(f"  {c:>8} | {cab:>6} | {ap}")
        print("")

        print("  DATOS OBTENIDOS DEL REPORTE")
        print("  " + "-" * 62)
        print("  Carrera  | Cab.   | Apuestas / Montos")
        print("  ---------+--------+----------------------------------------")
        for c in todas_carreras:
            info = datos_rep_norm.get(c)
            cab = info.get("caballos", 0) if info else 0
            ap = _formatear_apuestas(info.get("apuestas", {})) if info else "-"
            print(f"  {c:>8} | {cab:>6} | {ap}")
        print("")

    def _imprimir_tabla_laplata(datos_planilla, datos_reporte):
        """Imprime tabla comparativa Planilla (XLS) vs REPORTE para La Plata."""
        todas_carreras = sorted(set(datos_planilla.keys()) | set(datos_reporte.keys()))

        print("")
        print("  DATOS OBTENIDOS DE LA PLANILLA (XLS)")
        print("  " + "-" * 62)
        print("  Carrera  | Cab.   | Apuestas / Montos")
        print("  ---------+--------+----------------------------------------")
        for c in todas_carreras:
            info = datos_planilla.get(c)
            cab = info.get("caballos", 0) if info else 0
            ap = _formatear_apuestas(info.get("apuestas", {})) if info else "-"
            print(f"  {c:>8} | {cab:>6} | {ap}")
        print("")

        print("  DATOS OBTENIDOS DEL REPORTE")
        print("  " + "-" * 62)
        print("  Carrera  | Cab.   | Apuestas / Montos")
        print("  ---------+--------+----------------------------------------")
        for c in todas_carreras:
            info = datos_reporte.get(c)
            cab = info.get("caballos", 0) if info else 0
            ap = _formatear_apuestas(info.get("apuestas", {})) if info else "-"
            print(f"  {c:>8} | {cab:>6} | {ap}")
        print("")

    def _seleccionar_fecha_palermo(fechas):
        """
        Pide al usuario la fecha de Palermo a comparar.
        Retorna la fecha seleccionada (str) o None si cancela.
        """
        if not fechas:
            return None
        if len(fechas) == 1:
            fecha = fechas[0]
            print(f"Se utilizará la única fecha encontrada en el PDF: {fecha}\n")
            return fecha

        print("Fechas encontradas en el PDF de Palermo. Seleccione cuál desea usar para la comparación:")
        for idx, f in enumerate(fechas, start=1):
            print(f"{idx}. {f}")
        print()

        while True:
            eleccion = input(f"Ingrese un número (1-{len(fechas)}) o Enter para cancelar: ").strip()
            if not eleccion:
                print("Operación cancelada.\n")
                return None
            if not eleccion.isdigit():
                print("Entrada inválida. Debe ser un número.\n")
                continue
            idx = int(eleccion)
            if not (1 <= idx <= len(fechas)):
                print("Número fuera de rango. Intente nuevamente.\n")
                continue
            fecha = fechas[idx - 1]
            print(f"\nFecha seleccionada: {fecha}\n")
            return fecha

    def _imprimir_tablas_palermo(datos_pdf, fecha_seleccionada, ruta_reporte, apuestas_oficial):
        """
        Imprime tablas Palermo: PDF bases/apuestas vs REPORTE vs OFICIAL.
        """
        datos_rep_norm_pal, _ = _normalizar_reporte_palermo(ruta_reporte)  # Ignoramos codigos_con_all, solo mostramos
        apuestas_por_fecha = datos_pdf.get("apuestas_por_fecha", {})
        apuestas_pdf_pal = apuestas_por_fecha.get(fecha_seleccionada, {})
        oficial_por_carrera = {
            int(item.get("carrera")): set(item.get("apuestas") or [])
            for item in (apuestas_oficial or [])
        }
        todas_carreras = sorted(
            set(apuestas_pdf_pal.keys()) | set(datos_rep_norm_pal.keys()) | set(oficial_por_carrera.keys())
        )

        print()
        print("  DATOS OBTENIDOS DEL PDF (Bases y Apuestas Palermo)")
        print("  " + "-" * 62)
        print("  Carrera  | Apuestas (código=monto)")
        print("  ---------+----------------------------------------")
        for c in todas_carreras:
            ap_pdf = _formatear_apuestas(apuestas_pdf_pal.get(c, {}))
            print(f"  {c:>8} | {ap_pdf}")
        print()

        print("  DATOS OBTENIDOS DEL REPORTE ")
        print("  " + "-" * 62)
        print("  Carrera  | Apuestas (código=monto)")
        print("  ---------+----------------------------------------")
        for c in todas_carreras:
            ap_rep = _formatear_apuestas(datos_rep_norm_pal.get(c, {}))
            print(f"  {c:>8} | {ap_rep}")
        print()

        print("  DATOS OBTENIDOS DEL OFICIAL (PALERMO)")
        print("  " + "-" * 62)
        print("  Carrera  | Apuestas (código)")
        print("  ---------+----------------------------------------")
        for c in todas_carreras:
            aps_of = oficial_por_carrera.get(c, set())
            ap_of = _formatear_apuestas({codigo: None for codigo in sorted(aps_of)}) if aps_of else "-"
            print(f"  {c:>8} | {ap_of}")
        print()

    def _imprimir_tabla_posting_vs_reporte(datos_posting, datos_reporte):
        """Imprime dos tablas separadas (primero Posting, luego Reporte)
        para comparacion visual. Each table uses full terminal width.
        datos_posting/datos_reporte: tuplas (valores_por_carrera, codigos_con_all).
        """
        valores_posting, _ = datos_posting
        valores_reporte, _ = datos_reporte
        todas = sorted(set(valores_posting.keys()) | set(valores_reporte.keys()))

        print()
        print("  DATOS OBTENIDOS DEL POSTING PRICES")
        print("  " + "-" * 62)
        print("  Carrera  | Apuestas (código=monto)")
        print("  ---------+----------------------------------------")
        for c in todas:
            print(f"  {c:>8} | {_formatear_apuestas(valores_posting.get(c, {}))}")
        print()

        print("  DATOS OBTENIDOS DEL REPORTE")
        print("  " + "-" * 62)
        print("  Carrera  | Apuestas (código=monto)")
        print("  ---------+----------------------------------------")
        for c in todas:
            print(f"  {c:>8} | {_formatear_apuestas(valores_reporte.get(c, {}))}")
        print()

    def _menu_comparar(hipodromo_nombre):
        ruta_pdf_seleccionada = None
        ruta_reporte_seleccionado = None
        rutas_posting = []

        while True:
            _limpiar_pantalla()
            print("======================================")
            print(f" COMPARAR ARCHIVOS - {hipodromo_nombre.upper()}")
            print("======================================")
            print("1. Seleccionar programa oficial (PDF)")
            print("2. Seleccionar reporte (TXT)")
            print("3. Seleccionar Posting Prices (TXT)")
            print("4. COMPARAR ARCHIVOS")
            print("5. Volver al menú principal")
            print("======================================")

            if ruta_pdf_seleccionada:
                print(f"PDF seleccionado:           {ruta_pdf_seleccionada}")
            else:
                print("PDF seleccionado:           (ninguno)")

            if ruta_reporte_seleccionado:
                print(f"Reporte seleccionado:       {ruta_reporte_seleccionado}")
            else:
                print("Reporte seleccionado:       (ninguno)")

            if rutas_posting:
                print(f"Posting Prices seleccionado: {len(rutas_posting)} archivo(s)")
            else:
                print("Posting Prices seleccionado: (ninguno)")

            opcion = input("\nElija una opción (1-5): ").strip()
            print()

            if opcion == "1":
                print("Seleccione el programa oficial (PDF).")
                ruta = _seleccionar_archivo_gui({".pdf"}, "programa oficial (PDF)")
                if not ruta:
                    print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del PDF (Enter para cancelar): ", {".pdf"})
                if ruta:
                    ruta_pdf_seleccionada = ruta
                    print(f"PDF seleccionado: {ruta_pdf_seleccionada}\n")

            elif opcion == "2":
                print("Seleccione el reporte (TXT).")
                ruta = _seleccionar_archivo_gui({".txt"}, "reporte (TXT)")
                if not ruta:
                    print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del reporte TXT (Enter para cancelar): ", {".txt"})
                if ruta:
                    ruta_reporte_seleccionado = ruta
                    print(f"Reporte seleccionado: {ruta_reporte_seleccionado}\n")

            elif opcion == "3":
                print("Seleccione archivos de Posting Prices (TXT). Puede elegir hasta 2 archivos.")
                rutas_posting = []
                for i in range(1, 3):
                    print(f"Seleccione el archivo #{i} de Posting Prices (o cancele para terminar)...")
                    ruta = _seleccionar_archivo_gui({".txt"}, f"Posting Prices #{i} (TXT)")
                    if not ruta:
                        print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                        ruta = _pedir_ruta(f"Ruta del Posting Prices #{i} TXT (Enter para cancelar): ", {".txt"})
                    if not ruta:
                        if i == 1:
                            print("No se seleccionó ningún archivo de Posting Prices.\n")
                        else:
                            print("Selección de Posting Prices finalizada.\n")
                        break
                    rutas_posting.append(ruta)
                    print(f"Archivo #{i} seleccionado: {ruta}")
                if rutas_posting:
                    print(f"Posting Prices cargados: {len(rutas_posting)} archivo(s)\n")
                else:
                    print("No se cargaron archivos de Posting Prices.\n")
                input("Presione Enter para continuar...")

            elif opcion == "4":
                if not ruta_pdf_seleccionada or not ruta_reporte_seleccionado:
                    print("Debe seleccionar primero el PDF y el archivo de reporte (opciones 1 y 2).\n")
                    continue

                print(f"Comparando archivos para {hipodromo_nombre}...")
                print("Leyendo datos del PDF y del reporte, por favor espere...\n")
                try:
                    resultado_agente = _agente.comparar_san_isidro(
                        ruta_pdf_seleccionada,
                        ruta_reporte_seleccionado,
                    )
                    coincide = resultado_agente["coincide"]
                    diferencias = resultado_agente["diferencias"]
                    datos_pdf_norm = resultado_agente["datos_pdf"]
                    datos_rep_norm = resultado_agente["datos_reporte"]
                except Exception as e:
                    print(f"Ocurrió un error durante la comparación: {e}\n")
                    continue

                # Para SAN ISIDRO (y formatos similares) mostrar tabla comparativa
                if hipodromo_nombre.lower() == "san isidro":
                    try:
                        _imprimir_tabla_san_isidro(datos_pdf_norm, datos_rep_norm)
                    except Exception as e:
                        print(f"No se pudo mostrar la tabla detallada: {e}\n")

                if coincide:
                    print("COMPARACIÓN: todo coincide correctamente entre el PDF y el reporte.\n")
                else:
                    print("COMPARACIÓN: se encontraron diferencias (carreras con inconsistencias):")
                    for d in diferencias:
                        print(f"  - {d}")
                    print()

                # Comparación de Posting Prices vs reporte (si hay archivos seleccionados)
                if rutas_posting:
                    print("Comparando Posting Prices contra el reporte...\n")
                    try:
                        resultado_posting = _agente.comparar_posting(
                            rutas_posting,
                            ruta_reporte_seleccionado,
                        )
                        coincide_posting = resultado_posting["coincide"]
                        diferencias_posting = resultado_posting["diferencias"]
                    except Exception as e:
                        print(f"Ocurrió un error durante la comparación de Posting Prices: {e}\n")
                        input("Presione Enter para volver al menú de comparación...")
                        print()
                        continue

                    try:
                        datos_reporte_rsm = _normalizar_reporte_palermo(ruta_reporte_seleccionado)
                        _imprimir_tabla_posting_vs_reporte(resultado_posting["datos_posting"], datos_reporte_rsm)
                    except Exception as e:
                        print(f"No se pudo mostrar la tabla detallada de Posting Prices: {e}\n")

                    if coincide_posting:
                        print("COMPARACIÓN POSTING PRICES vs REPORTE: todos los valores coinciden.\n")
                    else:
                        print("COMPARACIÓN POSTING PRICES vs REPORTE: se encontraron diferencias:")
                        for d in diferencias_posting:
                            print(f"  - {d}")
                        print()

                input("Presione Enter para volver al menú de comparación...")
                print()

            elif opcion == "5":
                print("Volviendo al menú principal...\n")
                return

            else:
                print("Opción no válida. Intente nuevamente.\n")

    def _menu_palermo():
        """
        Menú específico para PALERMO.
        Permite seleccionar:
        - Bases y Apuestas Palermo (PDF)
        - Reporte (TXT)
        - Oficial (PDF)
        - Posting Prices (TXT)
        y compara apuestas, montos y/o valores contra el reporte.
        """
        ruta_base = os.path.dirname(__file__) or "."
        ruta_pdf_palermo = os.path.join(ruta_base, "palermo.pdf")
        if not os.path.isfile(ruta_pdf_palermo):
            ruta_pdf_palermo = None
        ruta_pdf_oficial = os.path.join(ruta_base, "oficial.pdf")
        if not os.path.isfile(ruta_pdf_oficial):
            ruta_pdf_oficial = None

        ruta_reporte = None
        apuestas_oficial = []
        rutas_posting = []

        while True:
            _limpiar_pantalla()
            print("======================================")
            print("      COMPARAR ARCHIVOS - PALERMO     ")
            print("======================================")
            print("1. Seleccionar archivo Bases y Apuestas Palermo (PDF)")
            print("2. Seleccionar reporte (TXT)")
            print("3. Seleccionar oficial (PDF)")
            print("4. Seleccionar Posting Prices (TXT)")
            print("5. COMPARAR ARCHIVOS")
            print("6. Volver al menú principal")
            print("======================================")

            if ruta_pdf_palermo:
                print(f" Bases y Apuestas Palermo (PDF): {ruta_pdf_palermo}")
            else:
                print("Bases y Apuestas Palermo (PDF): (ninguno)")

            if ruta_reporte:
                print(f"Reporte seleccionado:           {ruta_reporte}")
            else:
                print("Reporte seleccionado:           (ninguno)")

            if ruta_pdf_oficial:
                print(f"Oficial seleccionado:           {ruta_pdf_oficial}")
            else:
                print("Oficial seleccionado:           (ninguno)")

            if rutas_posting:
                print(f"Posting Prices seleccionado:    {len(rutas_posting)} archivo(s)")
            else:
                print("Posting Prices seleccionado:    (ninguno)")

            opcion = input("\nElija una opción (1-6): ").strip()
            print()

            if opcion == "1":
                print("Seleccione el archivo Bases y Apuestas (PDF) de PALERMO.")
                ruta = _seleccionar_archivo_gui({".pdf"}, "bases y apuestas PALERMO (PDF)")
                if not ruta:
                    print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del PDF de PALERMO (Enter para cancelar): ", {".pdf"})
                if ruta:
                    ruta_pdf_palermo = ruta
                    print(f"PDF de Palermo seleccionado: {ruta_pdf_palermo}\n")

            elif opcion == "2":
                print("Seleccione el reporte (TXT) para PALERMO.")
                ruta = _seleccionar_archivo_gui({".txt"}, "reporte PALERMO (TXT)")
                if not ruta:
                    print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del reporte TXT (Enter para cancelar): ", {".txt"})
                if ruta:
                    ruta_reporte = ruta
                    print(f"Reporte seleccionado: {ruta_reporte}\n")

            elif opcion == "4":
                print("Seleccione archivos de Posting Prices (TXT). Puede elegir hasta 2 archivos.")
                rutas_posting = []
                for i in range(1, 3):
                    print(f"Seleccione el archivo #{i} de Posting Prices (o cancele para terminar)...")
                    ruta = _seleccionar_archivo_gui({".txt"}, f"Posting Prices #{i} (TXT)")
                    if not ruta:
                        print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                        ruta = _pedir_ruta(f"Ruta del Posting Prices #{i} TXT (Enter para cancelar): ", {".txt"})
                    if not ruta:
                        if i == 1:
                            print("No se seleccionó ningún archivo de Posting Prices.\n")
                        else:
                            print("Selección de Posting Prices finalizada.\n")
                        break
                    rutas_posting.append(ruta)
                    print(f"Archivo #{i} seleccionado: {ruta}")
                if rutas_posting:
                    print(f"Posting Prices cargados: {len(rutas_posting)} archivo(s)\n")
                else:
                    print("No se cargaron archivos de Posting Prices.\n")
                input("Presione Enter para continuar...")

            elif opcion == "5":
                if not ruta_pdf_palermo:
                    print("Debe seleccionar primero el PDF de PALERMO (opción 1).\n")
                    continue

                if not ruta_reporte:
                    print("Debe seleccionar primero el archivo de reporte (opción 2).\n")
                    continue

                if not ruta_pdf_oficial:
                    print("Debe seleccionar también el OFICIAL (opción 3) para comparar los 3 archivos.\n")
                    continue

                print("Leyendo datos del PDF de Palermo, por favor espere...\n")

                try:
                    datos_pdf = _leer_palermo_desde_pdf(ruta_pdf_palermo)
                except Exception as e:
                    print(f"Ocurrió un error leyendo el PDF de Palermo: {e}\n")
                    continue

                fechas = datos_pdf.get("fechas", [])
                if not fechas:
                    print("No se encontraron fechas en el PDF de Palermo.\n")
                    continue

                fecha_seleccionada = _seleccionar_fecha_palermo(fechas)
                if not fecha_seleccionada:
                    continue

                print("Comparando PALERMO (apuestas y montos) con el reporte...")
                print("Esto puede demorar unos instantes...\n")

                try:
                    resultado_agente_palermo = _agente.comparar_palermo_con_oficial(
                        ruta_pdf_palermo,
                        ruta_reporte,
                        ruta_pdf_oficial,
                        fecha_objetivo=fecha_seleccionada,
                    )
                    bloque_palermo = resultado_agente_palermo["palermo_vs_reporte"]
                    bloque_oficial = resultado_agente_palermo["oficial_vs_reporte"]
                    coincide = bloque_palermo["coincide"]
                    diferencias = bloque_palermo["diferencias"]
                    coincide_oficial = bloque_oficial["coincide"]
                    diferencias_oficial = bloque_oficial["diferencias"]
                    apuestas_oficial = bloque_oficial["apuestas_oficial"]
                except Exception as e:
                    print(f"Ocurrió un error durante la comparación: {e}\n")
                    continue

                # Mostrar tablas de apuestas PDF vs REPORTE para PALERMO
                try:
                    _imprimir_tablas_palermo(datos_pdf, fecha_seleccionada, ruta_reporte, apuestas_oficial)
                except Exception as e:
                    print(f"No se pudo mostrar la tabla detallada de PALERMO: {e}\n")

                if coincide:
                    print("COMPARACIÓN PALERMO(bases y apuestas) contra REPORTE: todas las apuestas y montos coinciden para la fecha seleccionada.\n")
                else:
                    print("COMPARACIÓN PALERMO(bases y apuestas contra REPORTE: se encontraron diferencias en apuestas/montos para la fecha seleccionada:")
                    for d in diferencias:
                        print(f"  - {d}")
                    print()

                if coincide_oficial:
                    print("COMPARACIÓN OFICIAL contra REPORTE (apuestas por carrera): todo coincide.\n")
                else:
                    print("COMPARACIÓN OFICIAL contra REPORTE (apuestas por carrera): se encontraron diferencias:")
                    for d in diferencias_oficial:
                        print(f"  - {d}")
                    print()

                # Comparación de Posting Prices vs reporte (si hay archivos seleccionados)
                if rutas_posting:
                    print("Comparando Posting Prices contra el reporte...\n")
                    try:
                        resultado_posting = _agente.comparar_posting(
                            rutas_posting,
                            ruta_reporte,
                        )
                        coincide_posting = resultado_posting["coincide"]
                        diferencias_posting = resultado_posting["diferencias"]
                    except Exception as e:
                        print(f"Ocurrió un error durante la comparación de Posting Prices: {e}\n")
                        input("Presione Enter para volver al menú de Palermo...")
                        print()
                        continue

                    try:
                        datos_reporte_rsm = _normalizar_reporte_palermo(ruta_reporte)
                        _imprimir_tabla_posting_vs_reporte(resultado_posting["datos_posting"], datos_reporte_rsm)
                    except Exception as e:
                        print(f"No se pudo mostrar la tabla detallada de Posting Prices: {e}\n")

                    if coincide_posting:
                        print("COMPARACIÓN POSTING PRICES vs REPORTE: todos los valores coinciden.\n")
                    else:
                        print("COMPARACIÓN POSTING PRICES vs REPORTE: se encontraron diferencias:")
                        for d in diferencias_posting:
                            print(f"  - {d}")
                        print()

                input("Presione Enter para volver al menú de Palermo...")
                print()

            elif opcion == "3":
                print("Seleccione el archivo OFICIAL (PDF) de PALERMO.")
                ruta = _seleccionar_archivo_gui({".pdf"}, "oficial PALERMO (PDF)")
                if not ruta:
                    print("No se seleccionó ningún archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del oficial PDF (Enter para cancelar): ", {".pdf"})
                if not ruta:
                    continue

                ruta_pdf_oficial = ruta
                print(f"Oficial seleccionado: {ruta_pdf_oficial}")
                print("Leyendo carreras y apuestas desde el oficial...\n")
                try:
                    apuestas_oficial = _extraer_apuestas_desde_oficial_palermo(ruta_pdf_oficial)
                except Exception as e:
                    print(f"Ocurrió un error leyendo el oficial: {e}\n")
                    input("Presione Enter para continuar...")
                    continue

                if not apuestas_oficial:
                    print("No se encontraron líneas de 'APUESTAS A' en el oficial.\n")
                else:
                    print(f"Oficial cargado correctamente. Carreras leídas: {len(apuestas_oficial)}\n")

            elif opcion == "6":
                print("Volviendo al menú principal...\n")
                return

            else:
                print("Opción no válida. Intente nuevamente.\n")

    def _menu_laplata():
        """
        Menu especifico para LA PLATA.
        Permite seleccionar:
        - Planilla (XLS)
        - Reporte (TXT)
        - Posting Prices (TXT)
        y compara Planilla vs Reporte y/o Posting vs Reporte.
        """
        ruta_xls_seleccionada = None
        ruta_reporte_seleccionado = None
        rutas_posting = []

        while True:
            _limpiar_pantalla()
            print("======================================")
            print(f"      COMPARAR ARCHIVOS - LA PLATA     ")
            print("======================================")
            print("1. Seleccionar planilla (XLS)")
            print("2. Seleccionar reporte (TXT)")
            print("3. Seleccionar Posting Prices (TXT)")
            print("4. COMPARAR ARCHIVOS")
            print("5. Volver al menu principal")
            print("======================================")

            if ruta_xls_seleccionada:
                print(f"Planilla seleccionada:       {ruta_xls_seleccionada}")
            else:
                print("Planilla seleccionada:       (ninguno)")

            if ruta_reporte_seleccionado:
                print(f"Reporte seleccionado:        {ruta_reporte_seleccionado}")
            else:
                print("Reporte seleccionado:        (ninguno)")

            if rutas_posting:
                print(f"Posting Prices seleccionado: {len(rutas_posting)} archivo(s)")
            else:
                print("Posting Prices seleccionado: (ninguno)")

            opcion = input("\nElija una opcion (1-5): ").strip()
            print()

            if opcion == "1":
                print("Seleccione la planilla (XLS) de LA PLATA.")
                ruta = _seleccionar_archivo_gui({".xls", ".xlsx"}, "planilla LA PLATA (XLS)")
                if not ruta:
                    print("No se selecciono ningun archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta de la planilla XLS (Enter para cancelar): ", {".xls", ".xlsx"})
                if ruta:
                    ruta_xls_seleccionada = ruta
                    print(f"Planilla seleccionada: {ruta_xls_seleccionada}\n")

            elif opcion == "2":
                print("Seleccione el reporte (TXT) para LA PLATA.")
                ruta = _seleccionar_archivo_gui({".txt"}, "reporte LA PLATA (TXT)")
                if not ruta:
                    print("No se selecciono ningun archivo desde la ventana. Puede ingresar la ruta manualmente.")
                    ruta = _pedir_ruta("Ruta del reporte TXT (Enter para cancelar): ", {".txt"})
                if ruta:
                    ruta_reporte_seleccionado = ruta
                    print(f"Reporte seleccionado: {ruta_reporte_seleccionado}\n")

            elif opcion == "3":
                print("Seleccione archivos de Posting Prices (TXT). Puede elegir hasta 2 archivos.")
                rutas_posting = []
                for i in range(1, 3):
                    print(f"Seleccione el archivo #{i} de Posting Prices (o cancele para terminar)...")
                    ruta = _seleccionar_archivo_gui({".txt"}, f"Posting Prices #{i} (TXT)")
                    if not ruta:
                        print("No se selecciono ningun archivo desde la ventana. Puede ingresar la ruta manualmente.")
                        ruta = _pedir_ruta(f"Ruta del Posting Prices #{i} TXT (Enter para cancelar): ", {".txt"})
                    if not ruta:
                        if i == 1:
                            print("No se selecciono ningun archivo de Posting Prices.\n")
                        else:
                            print("Seleccion de Posting Prices finalizada.\n")
                        break
                    rutas_posting.append(ruta)
                    print(f"Archivo #{i} seleccionado: {ruta}")
                if rutas_posting:
                    print(f"Posting Prices cargados: {len(rutas_posting)} archivo(s)\n")
                else:
                    print("No se cargaron archivos de Posting Prices.\n")
                input("Presione Enter para continuar...")

            elif opcion == "4":
                if not ruta_xls_seleccionada or not ruta_reporte_seleccionado:
                    print("Debe seleccionar primero la planilla y el reporte (opciones 1 y 2).\n")
                    continue

                print("Comparando archivos para LA PLATA...")
                print("Leyendo datos de la planilla y del reporte, por favor espere...\n")
                try:
                    resultado_agente = _agente.comparar_laplata(
                        ruta_xls_seleccionada,
                        ruta_reporte_seleccionado,
                    )
                    coincide = resultado_agente["coincide"]
                    diferencias = resultado_agente["diferencias"]
                    datos_planilla_norm = resultado_agente["datos_planilla"]
                    datos_rep_norm = resultado_agente["datos_reporte"]
                except Exception as e:
                    print(f"Ocurrio un error durante la comparacion: {e}\n")
                    continue

                try:
                    _imprimir_tabla_laplata(datos_planilla_norm, datos_rep_norm)
                except Exception as e:
                    print(f"No se pudo mostrar la tabla detallada: {e}\n")

                if coincide:
                    print("COMPARACION: todo coincide correctamente entre la Planilla y el Reporte.\n")
                else:
                    print("COMPARACION: se encontraron diferencias:")
                    for d in diferencias:
                        print(f"  - {d}")
                    print()

                if rutas_posting:
                    print("Comparando Posting Prices contra el reporte...\n")
                    try:
                        resultado_posting = _agente.comparar_posting(
                            rutas_posting,
                            ruta_reporte_seleccionado,
                        )
                        coincide_posting = resultado_posting["coincide"]
                        diferencias_posting = resultado_posting["diferencias"]
                    except Exception as e:
                        print(f"Ocurrio un error durante la comparacion de Posting Prices: {e}\n")
                        input("Presione Enter para volver al menu de La Plata...")
                        print()
                        continue

                    try:
                        datos_reporte_rsm = _normalizar_reporte_palermo(ruta_reporte_seleccionado)
                        _imprimir_tabla_posting_vs_reporte(resultado_posting["datos_posting"], datos_reporte_rsm)
                    except Exception as e:
                        print(f"No se pudo mostrar la tabla detallada de Posting Prices: {e}\n")

                    if coincide_posting:
                        print("COMPARACION POSTING PRICES vs REPORTE: todos los valores coinciden.\n")
                    else:
                        print("COMPARACION POSTING PRICES vs REPORTE: se encontraron diferencias:")
                        for d in diferencias_posting:
                            print(f"  - {d}")
                        print()

                input("Presione Enter para volver al menu de La Plata...")
                print()

            elif opcion == "5":
                print("Volviendo al menu principal...\n")
                return

            else:
                print("Opcion no valida. Intente nuevamente.\n")

    # Menú principal
    while True:
        _limpiar_pantalla()
        print("======================================")
        print("           COMPARAR ARCHIVOS          ")
        print("======================================")
        print("1. SAN ISIDRO")
        print("2. PALERMO")
        print("3. LA PLATA")
        print("4. Salir")
        print("======================================")

        opcion = input("Seleccione el hipódromo (1-4): ").strip()
        print()

        if opcion == "1":
            _menu_comparar("San Isidro")
        elif opcion == "2":
            _menu_palermo()
        elif opcion == "3":
            _menu_laplata()
        elif opcion == "4":
            print("Saliendo del programa.")
            sys.exit(0)
        else:
            print("Opción no válida. Intente nuevamente.\n")