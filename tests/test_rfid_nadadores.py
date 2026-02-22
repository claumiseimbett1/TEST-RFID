"""
Tests unitarios para rfid_nadadores: CompetenciaManager y guardado de resultados.
Ejecutar desde la raíz del proyecto: pytest tests/ -v
"""
import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

_raiz = Path(__file__).resolve().parent.parent
if str(_raiz) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_raiz))

from rfid_nadadores import RFIDTag, CompetenciaManager


def _tag(epc_hex: str, rssi_raw: int = 127, antenna: int = 1, ts: datetime = None) -> RFIDTag:
    """Crea un RFIDTag; epc_hex debe ser 24 caracteres (12 bytes)."""
    if len(epc_hex) != 24:
        epc_hex = epc_hex.ljust(24, "0")[:24]
    return RFIDTag(
        epc=bytes.fromhex(epc_hex),
        rssi=rssi_raw,
        antenna=antenna,
        timestamp=ts or datetime(2025, 1, 15, 10, 0, 0),
    )


class TestCompetenciaManager:
    def test_iniciar_carrera_fija_punto_cero(self):
        m = CompetenciaManager()
        assert m.hora_inicio is None
        m.iniciar_carrera()
        assert m.hora_inicio is not None

    def test_registrar_llegada_aumenta_posicion(self):
        m = CompetenciaManager()
        m.iniciar_carrera()
        t1 = _tag("A" * 24)
        t2 = _tag("B" * 24)
        m.registrar_llegada(t1)
        m.registrar_llegada(t2)
        assert len(m.llegadas) == 2
        assert m.posicion_actual == 3
        assert m.llegadas[0][0] == 1 and m.llegadas[1][0] == 2

    def test_registrar_llegada_duplicado_no_suma(self):
        m = CompetenciaManager()
        m.iniciar_carrera()
        t = _tag("A" * 24)
        m.registrar_llegada(t)
        m.registrar_llegada(t)
        assert len(m.llegadas) == 1

    def test_obtener_resultados_formato(self):
        m = CompetenciaManager()
        m.iniciar_carrera()
        t = _tag("A" * 24)
        m.registrar_llegada(t)
        res = m.obtener_resultados()
        assert len(res) == 1
        r = res[0]
        assert "posicion" in r and r["posicion"] == 1
        assert "epc" in r and r["epc"] == "A" * 24
        assert "tiempo_carrera_s" in r
        assert "rssi" in r and "antenna" in r

    def test_tiempo_carrera_sin_punto_cero_es_none(self):
        m = CompetenciaManager()
        t = _tag("A" * 24)
        m.registrar_llegada(t)
        res = m.obtener_resultados()
        assert res[0]["tiempo_carrera_s"] is None

    def test_tiempo_carrera_con_punto_cero(self):
        m = CompetenciaManager()
        m.hora_inicio = datetime(2025, 1, 15, 10, 0, 0)
        t = _tag("A" * 24, ts=datetime(2025, 1, 15, 10, 0, 3))
        m.registrar_llegada(t)
        res = m.obtener_resultados()
        assert res[0]["tiempo_carrera_s"] is not None
        assert 2.9 <= res[0]["tiempo_carrera_s"] <= 3.1


class TestGuardarResultados:
    """Tests del guardado CSV (sin invocar cruzar_resultados)."""

    def test_guardar_escribe_csv_correcto(self):
        m = CompetenciaManager()
        m.iniciar_carrera()
        t = _tag("ABC1230000000000000000", ts=datetime(2025, 1, 15, 10, 0, 5))
        m.registrar_llegada(t)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "resultados_nadadores")
            csv_path = base + ".csv"
            # Evitar efectos del cruce (planilla en cwd); solo comprobamos el CSV de resultados
            with patch("cruzar_resultados.cruzar_resultados", return_value=False):
                m.guardar_resultados(nombre_base=base)
            assert os.path.isfile(csv_path)
            with open(csv_path, encoding="utf-8") as f:
                r = csv.reader(f)
                rows = list(r)
            assert any(row and row[0] == "inicio_punto_cero" for row in rows)
            assert any(row and row[0] == "posicion" for row in rows)
            header = next((r for r in rows if r and r[0] == "posicion"), None)
            assert header == ["posicion", "epc", "hora_llegada", "tiempo_carrera_s", "antena", "rssi"]
            data_row = next((r for r in rows if r and r[0] == "1"), None)
            assert data_row is not None
            # EPC en R300 es 24 hex (12 bytes); _tag rellena a 24 chars
            assert len(data_row[1]) == 24 and data_row[1].startswith("ABC123")
            assert len(data_row) >= 6

    def test_guardar_sin_punto_cero_sin_fila_inicio(self):
        m = CompetenciaManager()
        # No llamar iniciar_carrera
        t = _tag("A" * 24)
        m.registrar_llegada(t)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "res")
            with patch("cruzar_resultados.cruzar_resultados", return_value=False):
                m.guardar_resultados(nombre_base=base)
            with open(base + ".csv", encoding="utf-8") as f:
                lineas = f.readlines()
            # Sin punto cero no se escribe fila "inicio_punto_cero"
            assert not any("inicio_punto_cero" in l for l in lineas)
            # Sí hay cabecera y al menos una fila de datos
            first_data = next((l for l in lineas if l.strip() and "posicion" not in l and "inicio" not in l), None)
            assert first_data is not None
