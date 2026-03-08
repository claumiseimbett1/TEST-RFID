#!/usr/bin/env python3
"""
Genera clasificación por tiempo a partir de resultados_con_nadadores.csv:
- CSV y Excel con posición general, por categoría y por sexo.
- PDF con tablas: clasificación general, por categoría y por sexo.
"""
import csv
import io
import sys

CSV_ENTRADA = "resultados_con_nadadores.csv"
CSV_SALIDA = "clasificacion.csv"
XLSX_SALIDA = "clasificacion.xlsx"
PDF_SALIDA = "clasificacion.pdf"


def _leer_archivo_texto(archivo: str) -> str:
    """Lee el archivo probando utf-8, cp1252 y latin-1."""
    with open(archivo, "rb") as f:
        raw = f.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_tiempo(s: str):
    """Convierte tiempo_carrera_s a float; None si vacío o inválido."""
    if not s or not str(s).strip():
        return None
    try:
        return float(str(s).strip().replace(",", "."))
    except ValueError:
        return None


def cargar_resultados(ruta: str) -> list:
    """Carga resultados_con_nadadores.csv y devuelve lista de dicts."""
    contenido = _leer_archivo_texto(ruta)
    r = csv.reader(io.StringIO(contenido))
    filas = []
    cabecera = None
    for row in r:
        if not row:
            continue
        if row[0] == "inicio_punto_cero":
            continue
        if row[0] == "posicion":
            cabecera = row
            continue
        if cabecera is None or len(row) < len(cabecera):
            continue
        filas.append(dict(zip(cabecera, row)))
    return filas


def _asignar_posiciones(registros: list, clave_tiempo: str = "tiempo_carrera_s") -> list:
    """Ordena por tiempo (asc) y asigna posicion 1, 2, 3... (sin tiempo al final)."""
    con_tiempo = [(r, _parse_tiempo(r.get(clave_tiempo, ""))) for r in registros]
    con_tiempo.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else 0))
    for i, (r, _) in enumerate(con_tiempo, 1):
        r["_pos"] = i
    return [r for r, _ in con_tiempo]


def calcular_clasificaciones(registros: list) -> list:
    """Añade posicion_general, posicion_categoria, posicion_sexo a cada registro."""
    # Copia para no mutar el original al ordenar
    regs = [dict(r) for r in registros]
    for r in regs:
        r["_tiempo"] = _parse_tiempo(r.get("tiempo_carrera_s", ""))

    # Clasificación general
    ordenados = sorted(regs, key=lambda r: (r["_tiempo"] is None, r["_tiempo"] if r["_tiempo"] is not None else 0))
    for i, r in enumerate(ordenados, 1):
        r["posicion_general"] = i

    # Por categoría
    categorias = {}
    for r in regs:
        cat = (r.get("categoria_nombre") or "").strip() or "Sin categoría"
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(r)
    for cat, lista in categorias.items():
        lista_sort = sorted(lista, key=lambda r: (r["_tiempo"] is None, r["_tiempo"] if r["_tiempo"] is not None else 0))
        for i, r in enumerate(lista_sort, 1):
            r["posicion_categoria"] = i

    # Por sexo
    por_sexo = {}
    for r in regs:
        sexo = (r.get("genero") or "").strip() or "Sin dato"
        if sexo not in por_sexo:
            por_sexo[sexo] = []
        por_sexo[sexo].append(r)
    for sexo, lista in por_sexo.items():
        lista_sort = sorted(lista, key=lambda r: (r["_tiempo"] is None, r["_tiempo"] if r["_tiempo"] is not None else 0))
        for i, r in enumerate(lista_sort, 1):
            r["posicion_sexo"] = i

    for r in regs:
        r.pop("_tiempo", None)
    return sorted(regs, key=lambda r: r["posicion_general"])


def guardar_csv(registros: list, ruta: str) -> None:
    """Guarda CSV con columnas de posición general, categoría, sexo y datos."""
    if not registros:
        return
    cabecera = [
        "posicion_general", "posicion_categoria", "posicion_sexo",
        "nombre", "numero_corredor", "categoria_nombre", "genero", "distancia",
        "tiempo_carrera_s", "hora_llegada", "posicion", "epc", "antena", "rssi", "epc_en_planilla"
    ]
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cabecera, extrasaction="ignore")
        w.writeheader()
        for r in registros:
            w.writerow(r)
    print(f"✓ CSV guardado: {ruta}")


def guardar_excel(registros: list, ruta: str) -> None:
    """Guarda la clasificación en un libro Excel (.xlsx)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        print("⚠ Para exportar Excel instala: pip install openpyxl")
        return
    if not registros:
        return
    cabecera = [
        "posicion_general", "posicion_categoria", "posicion_sexo",
        "nombre", "numero_corredor", "categoria_nombre", "genero", "distancia",
        "tiempo_carrera_s", "hora_llegada", "posicion", "epc", "antena", "rssi", "epc_en_planilla"
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "Clasificación"
    for c, col in enumerate(cabecera, 1):
        cell = ws.cell(row=1, column=c, value=col)
        cell.font = Font(bold=True)
    for row_idx, r in enumerate(registros, 2):
        for c, col in enumerate(cabecera, 1):
            ws.cell(row=row_idx, column=c, value=r.get(col, ""))
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 14
    wb.save(ruta)
    print(f"✓ Excel guardado: {ruta}")


def guardar_pdf(registros: list, ruta: str) -> None:
    """Genera PDF con clasificación general, por categoría y por sexo."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("⚠ Para generar el PDF instala: pip install fpdf2")
        return
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Clasificación por tiempo", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Total participantes: {len(registros)}", ln=True, align="C")
    pdf.ln(8)

    def tabla(pdf, titulo: str, filas: list, columnas: list, anchos: list):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, titulo, ln=True)
        pdf.set_font("Helvetica", "B", 8)
        for col, w in zip(columnas, anchos):
            pdf.cell(w, 6, str(col)[:20], border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for row in filas:
            for k, w in zip(columnas, anchos):
                val = str(row.get(k, ""))[:20]
                pdf.cell(w, 5, val, border=1)
            pdf.ln()
        pdf.ln(4)

    # General
    col_gen = ["posicion_general", "nombre", "categoria_nombre", "genero", "tiempo_carrera_s"]
    w_gen = [18, 55, 40, 28, 28]
    tabla(pdf, "1. Clasificación general", registros, col_gen, w_gen)

    # Por categoría
    categorias = {}
    for r in registros:
        cat = (r.get("categoria_nombre") or "").strip() or "Sin categoría"
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(r)
    for cat in sorted(categorias.keys()):
        lista = sorted(categorias[cat], key=lambda r: r["posicion_categoria"])
        col_cat = ["posicion_categoria", "nombre", "genero", "tiempo_carrera_s"]
        w_cat = [22, 70, 35, 32]
        tabla(pdf, f"2. Por categoría: {cat}", lista, col_cat, w_cat)

    # Por sexo
    por_sexo = {}
    for r in registros:
        sexo = (r.get("genero") or "").strip() or "Sin dato"
        if sexo not in por_sexo:
            por_sexo[sexo] = []
        por_sexo[sexo].append(r)
    for sexo in sorted(por_sexo.keys()):
        lista = sorted(por_sexo[sexo], key=lambda r: r["posicion_sexo"])
        col_sex = ["posicion_sexo", "nombre", "categoria_nombre", "tiempo_carrera_s"]
        w_sex = [22, 70, 50, 35]
        tabla(pdf, f"3. Por sexo: {sexo}", lista, col_sex, w_sex)

    pdf.output(ruta)
    print(f"✓ PDF guardado: {ruta}")


def main(entrada: str = CSV_ENTRADA, salida_csv: str = CSV_SALIDA,
         salida_xlsx: str = XLSX_SALIDA, salida_pdf: str = PDF_SALIDA) -> bool:
    """Carga resultados, calcula clasificaciones y genera CSV, Excel y PDF."""
    try:
        registros = cargar_resultados(entrada)
    except FileNotFoundError:
        print(f"⚠ No se encontró {entrada}. Ejecuta antes: python cruzar_resultados.py")
        return False
    if not registros:
        print("⚠ No hay filas de resultados en el CSV.")
        return False
    con_pos = calcular_clasificaciones(registros)
    guardar_csv(con_pos, salida_csv)
    guardar_excel(con_pos, salida_xlsx)
    guardar_pdf(con_pos, salida_pdf)
    return True


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else CSV_ENTRADA
    if not main(entrada=entrada):
        sys.exit(1)
