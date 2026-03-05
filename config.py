#!/usr/bin/env python3
"""
Configuración común del lector R300 YRM200.
Usada por test_conexion.py y rfid_nadadores.py.
"""
# --- Ajusta a la IP y puerto de tu lector ---
LECTOR_IP = "192.168.0.178"
LECTOR_PORT = 4001

# Si tu lector usa otro algoritmo de checksum y las tramas dan "Checksum inválido", pon True para omitir la validación.
SKIP_CHECKSUM = True
