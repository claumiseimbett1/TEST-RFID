#!/usr/bin/env python3
"""
Cruza resultados de rfid_nadadores con la planilla de EPCs (generar_epcs).
Genera un CSV con posición, EPC, nombre, categoría, género, tiempo y datos del nadador.
Si existe nombres_nadadores.csv (columnas epc, nombre, categoria, sexo), se usa para el cruce.
"""
import csv
import io

# Archivos por defecto
PLANILLA_CSV = "tags_para_registro.csv"
NOMBRES_CSV = "nombres_nadadores.csv"  # Opcional: epc, nombre, categoria, sexo
RESULTADOS_CSV = "resultados_nadadores.csv"
SALIDA_CSV = "resultados_con_nadadores.csv"


def _segundos_a_hhmmss(segundos) -> str:
    """Convierte segundos (float o string numérico) a hh:mm:ss.ccc."""
    if segundos is None or (isinstance(segundos, str) and not segundos.strip()):
        return ""
    try:
        s = float(str(segundos).strip().replace(",", "."))
    except ValueError:
        return ""
    if s < 0 or s != s:
        return ""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}"


def _normalizar_epc(epc: str) -> str:
    """EPC sin espacios, mayúsculas; si tiene más de 24 hex se usan los últimos 24 (ej. 00E280... → E280...)."""
    s = (epc or "").replace(" ", "").strip().upper()
    s = "".join(c for c in s if c in "0123456789ABCDEF")
    if len(s) > 24:
        s = s[-24:]
    return s


def _leer_archivo_texto(archivo: str) -> str:
    """Lee el archivo probando utf-8, cp1252 y latin-1 (p. ej. CSV de Excel en Windows)."""
    with open(archivo, "rb") as f:
        raw = f.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _cargar_datos_nadadores_por_epc(archivo: str) -> dict:
    """Carga CSV con columnas epc, nombre, categoria, sexo. Acepta BOM y variantes (categoria_nombre, genero)."""
    out = {}
    try:
        contenido = _leer_archivo_texto(archivo)
        reader = csv.DictReader(io.StringIO(contenido))
        if not reader.fieldnames:
            return out
        keys = {k.strip().lstrip("\ufeff").lower(): k for k in reader.fieldnames}
        col_epc = keys.get("epc") or keys.get("epc_formateado") or reader.fieldnames[0]
        col_nombre = keys.get("nombre") or keys.get("nombre_nadador") or (reader.fieldnames[1] if len(reader.fieldnames) > 1 else "")
        col_categoria = keys.get("categoria") or keys.get("categoria_nombre")
        col_sexo = keys.get("sexo") or keys.get("genero")
        for row in reader:
            epc = (row.get(col_epc) or "").strip()
            key = _normalizar_epc(epc)
            if not key:
                continue
            nombre = (row.get(col_nombre) or "").strip() if col_nombre else ""
            categoria = (row.get(col_categoria) or "").strip() if col_categoria else ""
            genero = (row.get(col_sexo) or "").strip() if col_sexo else ""
            out[key] = {
                "nombre": nombre,
                "categoria_nombre": categoria,
                "genero": genero,
            }
    except FileNotFoundError:
        pass
    return out


def cruzar_resultados(
    planilla_csv: str = PLANILLA_CSV,
    resultados_csv: str = RESULTADOS_CSV,
    salida_csv: str = SALIDA_CSV,
    nombres_csv: str = NOMBRES_CSV,
) -> bool:
    """
    Lee la planilla de EPCs, opcionalmente nombres_nadadores.csv (epc, nombre, categoria, sexo),
    y los resultados de carrera; cruza por EPC y escribe resultados_con_nadadores.csv
    con posición, EPC, nombre, categoría, género (del archivo de nombres o planilla), número corredor, distancia, tiempos.
    """
    try:
        contenido = _leer_archivo_texto(planilla_csv)
        reader = csv.DictReader(io.StringIO(contenido))
        if not reader.fieldnames:
            return False
        planilla = list(reader)
    except FileNotFoundError:
        return False

    # Datos por EPC: nombre, categoría, sexo (archivo opcional)
    lookup_datos = _cargar_datos_nadadores_por_epc(nombres_csv) if nombres_csv else {}
    if lookup_datos:
        print(f"  Datos de cruce cargados: {len(lookup_datos)} filas desde {nombres_csv}")

    # Diccionario EPC normalizado -> datos del nadador (planilla)
    lookup = {}
    for row in planilla:
        epc_fmt = row.get("epc_formateado", "")
        epc_key = _normalizar_epc(epc_fmt)
        if epc_key:
            lookup[epc_key] = {
                "nombre": row.get("nombre", "").strip() or row.get("nombre_nadador", "").strip(),
                "numero_corredor": row.get("numero_corredor", ""),
                "categoria_nombre": row.get("categoria_nombre", ""),
                "genero": row.get("genero", ""),
                "distancia": row.get("distancia", ""),
                "edad_min": row.get("edad_min", ""),
                "edad_max": row.get("edad_max", ""),
            }

    if not lookup:
        return False

    try:
        contenido = _leer_archivo_texto(resultados_csv)
    except FileNotFoundError:
        return False

    # Parsear CSV: puede tener primera fila "inicio_punto_cero,..."
    filas_resultados = []
    inicio_punto_cero = None
    r = csv.reader(io.StringIO(contenido))
    for row in r:
        if not row:
            continue
        if row[0] == "inicio_punto_cero":
            inicio_punto_cero = row[1] if len(row) > 1 else None
            continue
        if row[0] == "posicion":
            continue
        filas_resultados.append(row)

    # Filas: posicion, epc, nombre, ..., validacion (epc_en_planilla)
    filas_salida = []
    cabecera = [
        "posicion", "epc", "nombre", "numero_corredor", "categoria_nombre", "genero", "distancia",
        "hora_llegada", "tiempo_carrera_s", "tiempo_carrera", "antena", "rssi", "edad_min", "edad_max",
        "epc_en_planilla"
    ]
    filas_salida.append(cabecera)

    epcs_no_en_planilla = []

    for row in filas_resultados:
        if len(row) < 2:
            continue
        posicion, epc = row[0], row[1]
        hora_llegada = row[2] if len(row) > 2 else ""
        tiempo_carrera_s = row[3] if len(row) > 3 else ""
        antena = row[4] if len(row) > 4 else ""
        rssi = row[5] if len(row) > 5 else ""

        epc_key = _normalizar_epc(epc)
        nadador = lookup.get(epc_key, {})
        en_planilla = epc_key in lookup
        if not en_planilla and epc_key:
            epcs_no_en_planilla.append(epc.strip())

        # Cruce: nombre, categoría y género del archivo de nombres (epc, nombre, categoria, sexo) o de la planilla
        datos_cruce = lookup_datos.get(epc_key, {})
        nombre = (datos_cruce.get("nombre") or "").strip() or nadador.get("nombre", "")
        categoria_nombre = (datos_cruce.get("categoria_nombre") or "").strip() or nadador.get("categoria_nombre", "")
        genero = (datos_cruce.get("genero") or "").strip() or nadador.get("genero", "")

        tiempo_carrera_fmt = _segundos_a_hhmmss(tiempo_carrera_s)
        validacion = "sí" if en_planilla else "no"
        filas_salida.append([
            posicion,
            epc,
            nombre,
            nadador.get("numero_corredor", ""),
            categoria_nombre,
            genero,
            nadador.get("distancia", ""),
            hora_llegada,
            tiempo_carrera_s,
            tiempo_carrera_fmt,
            antena,
            rssi,
            nadador.get("edad_min", ""),
            nadador.get("edad_max", ""),
            validacion,
        ])

    with open(salida_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if inicio_punto_cero is not None:
            w.writerow(["inicio_punto_cero", inicio_punto_cero])
        w.writerows(filas_salida)

    if epcs_no_en_planilla:
        print(f"  ⚠ Validación: {len(epcs_no_en_planilla)} EPC(s) no están en la planilla:")
        for e in epcs_no_en_planilla[:10]:
            print(f"     • {e}")
        if len(epcs_no_en_planilla) > 10:
            print(f"     ... y {len(epcs_no_en_planilla) - 10} más (revisa columna 'epc_en_planilla' en el CSV).")
        else:
            print("     Revisa la columna 'epc_en_planilla' en el CSV (filtrar por 'no').")

    # Clasificación por tiempo (CSV + PDF)
    try:
        from clasificacion import main as main_clasificacion
        if main_clasificacion(entrada=salida_csv):
            print("  Clasificación (general, categoría+sexo): CSV y PDF generados.")
    except Exception as e:
        print(f"  ⚠ Error al generar clasificación/PDF: {e}")
        print("     Para el PDF instala: pip install fpdf2")

    return True


if __name__ == "__main__":
    if cruzar_resultados():
        print(f"✓ Cruce guardado en {SALIDA_CSV}")
    else:
        print(f"⚠ No se pudo cruzar. Revisa que existan {PLANILLA_CSV} y {RESULTADOS_CSV}")
