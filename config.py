#!/usr/bin/env python3
"""Configuración lector R300 YRM200 (test_conexion.py, rfid_nadadores.py)."""
LECTOR_IP = "192.168.0.178"
LECTOR_PORT = 4001
SKIP_CHECKSUM = True
SEND_START_INVENTORY = True
NUM_ANTENNAS = 4
# Números de antena 1-4 (puertos del lector). Ej.: [3, 4] = solo antenas 3 y 4.
ANTENNAS_ACTIVAS = [3, 4]
# Mapeo 1-4 → número a mostrar. {} = sin cambio. Si en tu equipo salen al revés: {3: 4, 4: 3}.
MAPEO_ANTENAS = {}
