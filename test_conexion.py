#!/usr/bin/env python3
"""
Test de conexión TCP/IP para lector RFID R300 YRM200 (RFID reader module).
Verifica conectividad con el equipo y muestra los datos recibidos
(texto o hex). Interpreta tramas del protocolo (cabecera 0xA0).
"""
import socket

# --- Configuración del equipo R300 YRM200: ajusta a tu red ---
LECTOR_IP = "192.168.0.178"
LECTOR_PORT = 4001
# Algunas configuraciones usan puerto 6000:
# LECTOR_PORT = 6000

# Comandos del protocolo (para mostrar nombre en consola)
CMD_NOMBRES = {
    0x89: "Inventario real",
    0x8A: "Inventario real",
    0x8B: "Inventario real",
    0x90: "Tags desde buffer",
    0x91: "Tags desde buffer",
}


def main():
    print("Equipo: R300 YRM200 – RFID reader module")
    print(f"Conectando a {LECTOR_IP}:{LECTOR_PORT}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((LECTOR_IP, LECTOR_PORT))
        sock.settimeout(1.0)

        print("✓ Conectado al lector. Esperando datos (Ctrl+C para detener):\n")

        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                continue

            if not data:
                print("[Conexión cerrada por el lector]")
                break

            # Intentar mostrar como texto; si no, en hexadecimal
            try:
                texto = data.decode("utf-8", errors="replace").strip()
                if texto:
                    print(f"[TEXTO] {texto}", flush=True)
                    continue
            except Exception:
                pass

            hex_str = " ".join(f"{b:02X}" for b in data)
            print(f"[HEX] [{len(data)} bytes] {hex_str}", flush=True)

            # Trama R300 YRM200: [0xA0][Len][ReaderId][Cmd][Data...][Checksum]
            if len(data) >= 4 and data[0] == 0xA0:
                lon, reader_id, cmd = data[1], data[2], data[3]
                nombre_cmd = CMD_NOMBRES.get(cmd, "Otro")
                print(f"  → R300: Len={lon}, ReaderId={reader_id}, Cmd=0x{cmd:02X} ({nombre_cmd})")

    except socket.error as e:
        print(f"✗ Error de conexión: {e}")
        print(f"  Revisa: IP del R300 YRM200 ({LECTOR_IP}), puerto ({LECTOR_PORT}), red y que el lector esté encendido.")
    except KeyboardInterrupt:
        print("\n⏹ Detenido")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
