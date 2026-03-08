#!/usr/bin/env python3
"""
Cruza resultados de rfid_nadadores con la planilla de EPCs (generar_epcs).
Genera un CSV con posición, EPC, nombre (opcional), tiempo y datos del nadador.
Si existe nombres_nadadores.csv (columnas epc, nombre), se incluye el nombre en la salida.
"""
import csv
import io

# Archivos por defecto
PLANILLA_CSV = "tags_para_registro.csv"
NOMBRES_CSV = "nombres_nadadores.csv"  # Opcional: epc, nombre (identifica nadador por EPC)
RESULTADOS_CSV = "resultados_nadadores.csv"
SALIDA_CSV = "resultados_con_nadadores.csv"


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


def _cargar_nombres_por_epc(archivo: str) -> dict:
    """Carga archivo CSV con columnas epc y nombre. Acepta BOM y variantes de nombres (EPC, nombre_nadador)."""
    out = {}
    try:
        contenido = _leer_archivo_texto(archivo)
        reader = csv.DictReader(io.StringIO(contenido))
        if not reader.fieldnames:
            return out
        # Mapa nombre normalizado (sin BOM, minúsculas) -> clave real del CSV
        keys = {k.strip().lstrip("\ufeff").lower(): k for k in reader.fieldnames}
        col_epc = keys.get("epc") or keys.get("epc_formateado") or reader.fieldnames[0]
        col_nombre = keys.get("nombre") or keys.get("nombre_nadador") or (reader.fieldnames[1] if len(reader.fieldnames) > 1 else "")
        for row in reader:
            epc = (row.get(col_epc) or "").strip()
            nombre = (row.get(col_nombre) or "").strip() if col_nombre else ""
            key = _normalizar_epc(epc)
            if key and nombre:
                out[key] = nombre
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
    Lee la planilla de EPCs, opcionalmente nombres_nadadores.csv (epc, nombre),
    y los resultados de carrera; cruza por EPC y escribe resultados_con_nadadores.csv
    con posición, EPC, nombre (si existe), número corredor, categoría, género, distancia, tiempos.
    """
    try:
        contenido = _leer_archivo_texto(planilla_csv)
        reader = csv.DictReader(io.StringIO(contenido))
        if not reader.fieldnames:
            return False
        planilla = list(reader)
    except FileNotFoundError:
        return False

    # Nombres por EPC (archivo opcional)
    lookup_nombres = _cargar_nombres_por_epc(nombres_csv) if nombres_csv else {}
    if lookup_nombres:
        print(f"  Nombres cargados: {len(lookup_nombres)} desde {nombres_csv}")

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
        "hora_llegada", "tiempo_carrera_s", "antena", "rssi", "edad_min", "edad_max",
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

        nombre = lookup_nombres.get(epc_key, nadador.get("nombre", ""))
        validacion = "sí" if en_planilla else "no"
        filas_salida.append([
            posicion,
            epc,
            nombre,
            nadador.get("numero_corredor", ""),
            nadador.get("categoria_nombre", ""),
            nadador.get("genero", ""),
            nadador.get("distancia", ""),
            hora_llegada,
            tiempo_carrera_s,
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

    return True


if __name__ == "__main__":
    if cruzar_resultados():
        print(f"✓ Cruce guardado en {SALIDA_CSV}")
    else:
        print(f"⚠ No se pudo cruzar. Revisa que existan {PLANILLA_CSV} y {RESULTADOS_CSV}")
