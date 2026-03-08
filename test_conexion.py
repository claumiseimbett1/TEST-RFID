#!/usr/bin/env python3
"""Test conexión TCP al lector R300 YRM200. Muestra tags (EPC, Ant, RSSI) y rotación de antenas."""
import socket
import struct
import time
from config import LECTOR_IP, LECTOR_PORT

HEADER = 0xA0


def parse_tag_en_trama(frame: bytes, antena_rotacion: int = None) -> None:
    """Extrae EPC, Ant y RSSI de trama 0x89 y los imprime. antena_rotacion sustituye Ant si se pasa."""
    if len(frame) < 22 or frame[0] != HEADER or frame[3] != 0x89:
        return
    if frame[1] < 17:
        return
    payload = frame[3 : 2 + frame[1]]
    if len(payload) < 17:
        return
    freq_ant, rssi_raw = payload[1], payload[-1]
    ant_no = freq_ant & 0x03
    rssi_h = (rssi_raw & 0x80) >> 7
    ant = min(ant_no + (4 if rssi_h else 0) + 1, 4)
    rssi_dbm = (rssi_raw & 0x7F) - 129
    epc_hex = payload[4:4 + 12].hex().upper()
    ant_mostrar = antena_rotacion if antena_rotacion is not None else ant
    print(f"  🏷 Tag leído: EPC={epc_hex}  Ant={ant_mostrar}  RSSI={rssi_dbm} dBm", flush=True)


def checksum(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result & 0xFF


def send_cmd(sock, cmd: int, reader_id: int = 0xFF, data: bytes = b''):
    """Envía trama: 0xA0 [len] [reader_id] [cmd] [data] checksum."""
    data_len = 3 + len(data)
    frame = struct.pack('BBB', HEADER, data_len, reader_id)
    frame += struct.pack('B', cmd)
    frame += data
    frame += struct.pack('B', checksum(frame))
    sock.send(frame)


def send_set_work_antenna(sock, antenna_id: int, reader_id: int = 0x01):
    """0x74: fija antena de trabajo (0..3 = Ant1..Ant4)."""
    send_cmd(sock, 0x74, reader_id, bytes([antenna_id & 0x03]))
    time.sleep(0.05)


def send_set_output_power(sock, power_dbm: int, reader_id: int = 0x01):
    """0x76: potencia RF 20-33 dBm."""
    val = max(20, min(33, power_dbm))
    send_cmd(sock, 0x76, reader_id, bytes([val]))
    time.sleep(0.05)


def send_start_inventory(sock, antenna_id: int = 0):
    """Fija antena (0x74), luego 0x89 y 0x80/0x90."""
    ant = antenna_id & 0x03
    for rid in (0x01, 0xFF):
        send_set_work_antenna(sock, ant, rid)
        time.sleep(0.05)
    time.sleep(0.2)
    send_cmd(sock, 0x89, 0x01, b'\xFF')
    time.sleep(0.1)
    send_cmd(sock, 0x89, 0xFF, b'\xFF')
    send_cmd(sock, 0x80, 0x01, b'\xFF')
    time.sleep(0.35)
    send_cmd(sock, 0x90, 0x01)


def main():
    print("Equipo: R300 YRM200 – RFID reader module")
    print(f"Conectando a {LECTOR_IP}:{LECTOR_PORT}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((LECTOR_IP, LECTOR_PORT))
        sock.settimeout(1.0)
        print("✓ Conectado al lector.")

        send_set_output_power(sock, 30, 0x01)
        send_set_output_power(sock, 30, 0xFF)
        time.sleep(0.1)
        try:
            from config import SEND_START_INVENTORY, ANTENNAS_ACTIVAS, MAPEO_ANTENAS
        except ImportError:
            SEND_START_INVENTORY = True
            ANTENNAS_ACTIVAS = [1, 2, 3, 4]
            MAPEO_ANTENAS = {}
        n_ant = len(ANTENNAS_ACTIVAS) or 1
        def _num_antena(ant_1based: int) -> int:
            return MAPEO_ANTENAS.get(ant_1based, ant_1based)
        if SEND_START_INVENTORY:
            send_start_inventory(sock, (ANTENNAS_ACTIVAS[0] - 1) if ANTENNAS_ACTIVAS else 0)
        nums = [_num_antena(a) for a in ANTENNAS_ACTIVAS]
        print(f"\nAcerca un tag. Se rotan antenas {nums} cada 0.5 s.")
        print("\nEsperando datos (Ctrl+C para detener):\n")

        ultimo_aviso = 0
        ultimo_cmd = time.time()
        REENVIAR_CADA = 0.5
        antena_idx = 0
        antena_actual = _num_antena(ANTENNAS_ACTIVAS[0]) if ANTENNAS_ACTIVAS else 1
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                now = time.time()
                if now - ultimo_cmd >= REENVIAR_CADA:
                    ant_num = ANTENNAS_ACTIVAS[antena_idx % n_ant]
                    ant = ant_num - 1
                    antena_actual = _num_antena(ant_num)
                    send_set_work_antenna(sock, ant, 0x01)
                    print(f"  [Rotación → Antena {antena_actual}]", flush=True)
                    time.sleep(0.2)
                    send_cmd(sock, 0x89, 0x01, b'\xFF')
                    time.sleep(0.25)
                    send_cmd(sock, 0x80, 0x01, b'\xFF')
                    time.sleep(0.3)
                    send_cmd(sock, 0x90, 0x01)
                    antena_idx += 1
                    ultimo_cmd = now
                if now - ultimo_aviso > 10:
                    print("  (esperando datos... acerca un tag)", flush=True)
                    ultimo_aviso = now
                continue

            if not data:
                print("[Conexión cerrada por el lector]")
                break
            buf = bytearray(data)
            while len(buf) >= 4 and buf[0] == 0xA0:
                lon = buf[1]
                frame_len = 2 + lon
                if len(buf) < frame_len:
                    break
                frame = bytes(buf[:frame_len])
                buf = buf[frame_len:]
                if frame[3] == 0x89 and lon >= 17:
                    parse_tag_en_trama(frame, antena_rotacion=antena_actual)
            continue

    except socket.error as e:
        print(f"✗ Error de conexión: {e}")
    except KeyboardInterrupt:
        print("\n⏹ Detenido")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
