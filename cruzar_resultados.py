#!/usr/bin/env python3
"""
Cruza resultados de rfid_nadadores con la planilla de EPCs (generar_epcs).
Genera un CSV con posición, EPC, nombre (opcional), tiempo y datos del nadador.
Si existe nombres_nadadores.csv (columnas epc, nombre), se incluye el nombre en la salida.
"""
import csv

# Archivos por defecto
PLANILLA_CSV = "tags_para_registro.csv"
NOMBRES_CSV = "nombres_nadadores.csv"  # Opcional: epc, nombre (identifica nadador por EPC)
RESULTADOS_CSV = "resultados_nadadores.csv"
SALIDA_CSV = "resultados_con_nadadores.csv"


def _normalizar_epc(epc: str) -> str:
    """EPC sin espacios y en mayúsculas para comparar."""
    return (epc or "").replace(" ", "").strip().upper()


def _cargar_nombres_por_epc(archivo: str) -> dict:
    """Carga archivo CSV con columnas epc (o epc_formateado) y nombre. Retorna dict EPC_normalizado -> nombre."""
    out = {}
    try:
        with open(archivo, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return out
            for row in reader:
                epc = row.get("epc") or row.get("epc_formateado") or ""
                nombre = row.get("nombre") or row.get("nombre_nadador") or ""
                key = _normalizar_epc(epc)
                if key and nombre:
                    out[key] = nombre.strip()
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
        with open(planilla_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return False
            planilla = list(reader)
    except FileNotFoundError:
        return False

    # Nombres por EPC (archivo opcional)
    lookup_nombres = _cargar_nombres_por_epc(nombres_csv) if nombres_csv else {}

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
        with open(resultados_csv, encoding="utf-8") as f:
            lineas = f.readlines()
    except FileNotFoundError:
        return False

    # Parsear CSV: puede tener primera fila "inicio_punto_cero,..."
    filas_resultados = []
    inicio_punto_cero = None
    r = csv.reader(lineas)
    for row in r:
        if not row:
            continue
        if row[0] == "inicio_punto_cero":
            inicio_punto_cero = row[1] if len(row) > 1 else None
            continue
        if row[0] == "posicion":
            continue
        filas_resultados.append(row)

    # Filas: posicion, epc, nombre, numero_corredor, categoria_nombre, genero, distancia, ...
    filas_salida = []
    cabecera = [
        "posicion", "epc", "nombre", "numero_corredor", "categoria_nombre", "genero", "distancia",
        "hora_llegada", "tiempo_carrera_s", "antena", "rssi", "edad_min", "edad_max"
    ]
    filas_salida.append(cabecera)

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
        nombre = lookup_nombres.get(epc_key, nadador.get("nombre", ""))
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
        ])

    with open(salida_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if inicio_punto_cero is not None:
            w.writerow(["inicio_punto_cero", inicio_punto_cero])
        w.writerows(filas_salida)

    return True


if __name__ == "__main__":
    if cruzar_resultados():
        print(f"✓ Cruce guardado en {SALIDA_CSV}")
    else:
        print(f"⚠ No se pudo cruzar. Revisa que existan {PLANILLA_CSV} y {RESULTADOS_CSV}")
