"""
Tests unitarios y de integración para cruzar_resultados.
Ejecutar desde la raíz del proyecto: pytest tests/ -v
"""
import csv
import os
import tempfile
from pathlib import Path

import pytest

# Asegurar import desde raíz del proyecto
import sys
_raiz = Path(__file__).resolve().parent.parent
if str(_raiz) not in sys.path:
    sys.path.insert(0, str(_raiz))

from cruzar_resultados import (
    _normalizar_epc,
    _cargar_nombres_por_epc,
    cruzar_resultados,
    PLANILLA_CSV,
    RESULTADOS_CSV,
    SALIDA_CSV,
    NOMBRES_CSV,
)


class TestNormalizarEpc:
    def test_mayusculas(self):
        assert _normalizar_epc("abc123") == "ABC123"

    def test_sin_espacios(self):
        assert _normalizar_epc("  AB C1 23  ") == "ABC123"

    def test_vacio(self):
        assert _normalizar_epc("") == ""
        assert _normalizar_epc("   ") == ""

    def test_mezcla(self):
        assert _normalizar_epc("  a1b2c3  ") == "A1B2C3"


class TestCargarNombresPorEpc:
    def test_archivo_no_existe(self):
        assert _cargar_nombres_por_epc("no_existe_xyz.csv") == {}

    def test_epc_y_nombre(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epc", "nombre"])
            w.writeheader()
            w.writerow({"epc": "ABC123", "nombre": "Juan Pérez"})
            w.writerow({"epc": "DEF456", "nombre": "María García"})
            path = f.name
        try:
            out = _cargar_nombres_por_epc(path)
            assert out["ABC123"] == "Juan Pérez"
            assert out["DEF456"] == "María García"
        finally:
            os.unlink(path)

    def test_epc_formateado(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epc_formateado", "nombre"])
            w.writeheader()
            w.writerow({"epc_formateado": "  xyz789 ", "nombre": "Ana"})
            path = f.name
        try:
            out = _cargar_nombres_por_epc(path)
            assert out["XYZ789"] == "Ana"
        finally:
            os.unlink(path)


class TestCruzarResultados:
    """Tests de integración del cruce con archivos temporales."""

    def _escribir_planilla(self, path: str, filas: list):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["epc_formateado", "nombre", "numero_corredor", "categoria_nombre", "genero", "distancia", "edad_min", "edad_max"],
                extrasaction="ignore",
            )
            w.writeheader()
            for row in filas:
                w.writerow(row)

    def _escribir_resultados(self, path: str, inicio_punto_cero: str = None, filas: list = None):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if inicio_punto_cero:
                w.writerow(["inicio_punto_cero", inicio_punto_cero])
            w.writerow(["posicion", "epc", "hora_llegada", "tiempo_carrera_s", "antena", "rssi"])
            for row in (filas or []):
                w.writerow(row)

    def _leer_salida(self, path: str) -> tuple:
        with open(path, encoding="utf-8") as f:
            r = csv.reader(f)
            rows = list(r)
        cabecera = None
        inicio = None
        datos = []
        for row in rows:
            if not row:
                continue
            if row[0] == "inicio_punto_cero":
                inicio = row[1] if len(row) > 1 else None
                continue
            if row[0] == "posicion":
                cabecera = row
                continue
            datos.append(row)
        return cabecera, inicio, datos

    def test_planilla_falta_retorna_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = os.path.join(tmp, "res.csv")
            out = os.path.join(tmp, "out.csv")
            self._escribir_resultados(res, filas=[["1", "ABC123", "10:00:00", "12.5", "1", "-50"]])
            ok = cruzar_resultados(planilla_csv=os.path.join(tmp, "no_existe.csv"), resultados_csv=res, salida_csv=out)
        assert ok is False

    def test_resultados_faltan_retorna_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.join(tmp, "planilla.csv")
            out = os.path.join(tmp, "out.csv")
            self._escribir_planilla(plan, [{"epc_formateado": "ABC123", "numero_corredor": "1", "categoria_nombre": "Libre", "genero": "M", "distancia": "100"}])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=os.path.join(tmp, "no_existe.csv"), salida_csv=out)
        assert ok is False

    def test_planilla_vacia_retorna_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.join(tmp, "planilla.csv")
            res = os.path.join(tmp, "res.csv")
            out = os.path.join(tmp, "out.csv")
            with open(plan, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["epc_formateado"])
                w.writeheader()
            self._escribir_resultados(res, filas=[["1", "ABC123", "10:00:00", "12.5", "1", "-50"]])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out)
        assert ok is False

    def test_cruce_epc_en_planilla_si(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.abspath(os.path.join(tmp, "planilla.csv"))
            res = os.path.abspath(os.path.join(tmp, "res.csv"))
            out = os.path.abspath(os.path.join(tmp, "out.csv"))
            self._escribir_planilla(plan, [
                {"epc_formateado": "ABC123", "nombre": "Juan", "numero_corredor": "1", "categoria_nombre": "Libre", "genero": "M", "distancia": "100", "edad_min": "18", "edad_max": "29"},
            ])
            self._escribir_resultados(res, inicio_punto_cero="2025-01-01 10:00:00", filas=[
                ["1", "ABC123", "10:00:12.500", "12.500", "1", "-50"],
            ])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out)
            assert ok is True
            assert os.path.isfile(out), f"Salida no creada en {out}; archivos en tmp: {os.listdir(tmp)}"
            cab, inicio, datos = self._leer_salida(out)
            assert "epc_en_planilla" in (cab or [])
            assert len(datos) == 1
            assert datos[0][1] == "ABC123"  # epc
            assert datos[0][2] == "Juan"    # nombre
            assert datos[0][-1] == "sí"     # epc_en_planilla
            assert inicio == "2025-01-01 10:00:00"

    def test_cruce_epc_no_en_planilla_no(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.abspath(os.path.join(tmp, "planilla.csv"))
            res = os.path.abspath(os.path.join(tmp, "res.csv"))
            out = os.path.abspath(os.path.join(tmp, "out.csv"))
            self._escribir_planilla(plan, [
                {"epc_formateado": "SOLOESTE", "numero_corredor": "1", "categoria_nombre": "Libre", "genero": "M", "distancia": "100"},
            ])
            self._escribir_resultados(res, filas=[
                ["1", "OTROEPC999", "10:00:00", "0", "1", "-50"],
            ])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out)
            assert ok is True
            assert os.path.isfile(out)
            cab, _, datos = self._leer_salida(out)
            assert len(datos) == 1
            assert datos[0][1] == "OTROEPC999"
            assert datos[0][-1] == "no"

    def test_cruce_normaliza_epc(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.abspath(os.path.join(tmp, "planilla.csv"))
            res = os.path.abspath(os.path.join(tmp, "res.csv"))
            out = os.path.abspath(os.path.join(tmp, "out.csv"))
            self._escribir_planilla(plan, [
                {"epc_formateado": "abc123", "numero_corredor": "1", "categoria_nombre": "Libre", "genero": "F", "distancia": "50"},
            ])
            self._escribir_resultados(res, filas=[
                ["1", "  ABC123  ", "10:00:00", "10", "1", "-48"],
            ])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out)
            assert ok is True
            assert os.path.isfile(out)
            _, _, datos = self._leer_salida(out)
            assert datos[0][-1] == "sí"

    def test_cruce_con_nombres_csv_opcional(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.abspath(os.path.join(tmp, "planilla.csv"))
            nombres = os.path.abspath(os.path.join(tmp, "nombres.csv"))
            res = os.path.abspath(os.path.join(tmp, "res.csv"))
            out = os.path.abspath(os.path.join(tmp, "out.csv"))
            self._escribir_planilla(plan, [
                {"epc_formateado": "ABC123", "nombre": "Planilla", "numero_corredor": "1", "categoria_nombre": "Libre", "genero": "M", "distancia": "100"},
            ])
            with open(nombres, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["epc", "nombre"])
                w.writeheader()
                w.writerow({"epc": "ABC123", "nombre": "Nombre desde nombres_nadadores"})
            self._escribir_resultados(res, filas=[["1", "ABC123", "10:00:00", "12", "1", "-50"]])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out, nombres_csv=nombres)
            assert ok is True
            assert os.path.isfile(out)
            _, _, datos = self._leer_salida(out)
            assert datos[0][2] == "Nombre desde nombres_nadadores"

    def test_varias_filas_mezcla_si_no(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = os.path.abspath(os.path.join(tmp, "planilla.csv"))
            res = os.path.abspath(os.path.join(tmp, "res.csv"))
            out = os.path.abspath(os.path.join(tmp, "out.csv"))
            self._escribir_planilla(plan, [
                {"epc_formateado": "UNO", "numero_corredor": "1", "categoria_nombre": "A", "genero": "M", "distancia": "100"},
                {"epc_formateado": "TRES", "numero_corredor": "3", "categoria_nombre": "A", "genero": "M", "distancia": "100"},
            ])
            self._escribir_resultados(res, filas=[
                ["1", "UNO", "10:00:01", "1", "1", "-50"],
                ["2", "NONEXISTE", "10:00:02", "2", "1", "-50"],
                ["3", "TRES", "10:00:03", "3", "1", "-50"],
            ])
            ok = cruzar_resultados(planilla_csv=plan, resultados_csv=res, salida_csv=out)
            assert ok is True
            assert os.path.isfile(out)
            _, _, datos = self._leer_salida(out)
            assert len(datos) == 3
            assert datos[0][-1] == "sí" and datos[0][1] == "UNO"
            assert datos[1][-1] == "no" and datos[1][1] == "NONEXISTE"
            assert datos[2][-1] == "sí" and datos[2][1] == "TRES"
