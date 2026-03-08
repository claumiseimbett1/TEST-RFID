#!/usr/bin/env python3
"""Lector RFID R300 YRM200 para control de nadadores. Protocolo: 0xA0 [Len] [ReaderId] [Cmd] [Data] [Checksum]."""
import csv
import socket
import struct
import time
from datetime import datetime
from typing import Optional, List, Tuple

EPC_LEN_HEX = 24


def es_epc_valido(epc: str) -> bool:
    """True si el EPC es un tag real (no placeholder/ruido como 000000)."""
    if not epc or len(epc.strip()) < 12:
        return False
    return not all(c == '0' for c in (epc or "").strip().upper())


class RFIDTag:
    """Tag RFID detectado (EPC 24 hex, RSSI dBm, antena, timestamp)."""
    def __init__(self, epc: bytes, rssi: int, antenna: int, timestamp: datetime):
        self.epc = epc.hex().upper()
        self.rssi = rssi - 129
        self.antenna = antenna
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"Tag(EPC={self.epc}, RSSI={self.rssi}dBm, Ant={self.antenna}, Time={self.timestamp.strftime('%H:%M:%S.%f')[:-3]})"


class RFIDReader:
    """Cliente TCP lector R300 YRM200."""
    HEADER = 0xA0
    CMD_INVENTORY = 0x89
    CMD_BUFFER = 0x90
    
    def __init__(self, ip: str, port: int = 6000):
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.buffer = bytearray()
        self.running = False
        
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            print(f"✓ Conectado a {self.ip}:{self.port}")
            try:
                from config import SEND_START_INVENTORY
            except ImportError:
                SEND_START_INVENTORY = True
            if SEND_START_INVENTORY:
                self.send_command(0x76, b'\x1E', reader_id=0x01)
                self.send_command(0x76, b'\x1E', reader_id=0xFF)
                time.sleep(0.08)
                try:
                    from config import ANTENNAS_ACTIVAS
                except ImportError:
                    ANTENNAS_ACTIVAS = [1, 2, 3, 4]
                ant = (ANTENNAS_ACTIVAS[0] - 1) if ANTENNAS_ACTIVAS else 0
                self.send_command(0x74, bytes([ant & 0x03]), reader_id=0x01)
                time.sleep(0.05)
                self.send_command(0x74, bytes([ant & 0x03]), reader_id=0xFF)
                time.sleep(0.2)
                self.send_command(0x89, b'\xFF', reader_id=0x01)
                time.sleep(0.15)
                self.send_command(0x89, b'\xFF', reader_id=0xFF)
            return True
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False
    
    def disconnect(self):
        self.running = False
        if self.socket:
            self.socket.close()
            print("✓ Desconectado")
    
    @staticmethod
    def checksum(data: bytes) -> int:
        result = 0
        for b in data:
            result ^= b
        return result & 0xFF
    
    def send_command(self, cmd: int, data: bytes = b'', reader_id: int = 0xFF):
        data_len = len(data) + 3
        frame = struct.pack('BBB', self.HEADER, data_len, reader_id)
        frame += struct.pack('B', cmd) + data
        frame += struct.pack('B', self.checksum(frame))
        
        self.socket.send(frame)
    
    def parse_frame(self, frame: bytes) -> Optional[dict]:
        if len(frame) < 5 or frame[0] != self.HEADER:
            return None
        try:
            from config import SKIP_CHECKSUM
        except ImportError:
            SKIP_CHECKSUM = False
        if not SKIP_CHECKSUM and self.checksum(frame[:-1]) != frame[-1]:
            print("⚠ Checksum inválido")
            return None
        
        data_len = frame[1]
        reader_id = frame[2]
        cmd = frame[3]
        data = frame[4:-1] if len(frame) > 5 else b''
        
        return {
            'cmd': cmd,
            'reader_id': reader_id,
            'data': data
        }
    
    def parse_inventory_tag(self, data: bytes, cmd: int) -> Optional[RFIDTag]:
        """Formato: [FreqAnt][PC(2)][EPC(N)][Rssi]."""
        if len(data) < 5:
            return None
        idx = 0
        freq_ant = data[idx]
        idx += 2  # PC
        epc_len = len(data) - idx - 1
        epc = data[idx:idx+epc_len]
        idx += epc_len
        rssi_raw = data[idx]
        ant_no = freq_ant & 0x03
        rssi_h = (rssi_raw & 0x80) >> 7
        rssi = rssi_raw & 0x7F
        antenna_raw = ant_no + (4 if rssi_h == 1 else 0) + 1
        antenna = self._clamp_antenna(antenna_raw)
        return RFIDTag(epc, rssi, antenna, datetime.now())
    
    def _clamp_antenna(self, antenna_raw: int) -> int:
        try:
            from config import NUM_ANTENNAS
        except ImportError:
            NUM_ANTENNAS = 8
        return min(max(1, antenna_raw), NUM_ANTENNAS)
    
    def parse_buffer_tag(self, data: bytes) -> Optional[RFIDTag]:
        """Formato: [TagCount(2)][DataLen][PC(2)][EPC(N)][CRC(2)][Rssi][FreqAnt][ReadCount]."""
        if len(data) < 9:
            return None
        data_len = data[2]
        epc_len = data_len - 4
        if 5 + epc_len + 2 + 1 + 1 > len(data):
            return None
        epc = data[5:5+epc_len]
        rssi_raw = data[5 + epc_len + 2]
        freq_ant = data[5 + epc_len + 3]
        ant_no = freq_ant & 0x03
        rssi_h = (rssi_raw & 0x80) >> 7
        rssi = rssi_raw & 0x7F
        antenna_raw = ant_no + (4 if rssi_h == 1 else 0) + 1
        antenna = self._clamp_antenna(antenna_raw)
        return RFIDTag(epc, rssi, antenna, datetime.now())
    
    def read_tags_continuous(self, callback=None, duration: int = None):
        """Lee tags en bucle; callback(tag) por cada uno. duration=None = infinito."""
        self.running = True
        start_time = time.time()
        try:
            from config import ANTENNAS_ACTIVAS, MAPEO_ANTENAS
        except ImportError:
            ANTENNAS_ACTIVAS = [1, 2, 3, 4]
            MAPEO_ANTENAS = {}
        n_ant = len(ANTENNAS_ACTIVAS) or 1
        def _num_antena(ant_1based: int) -> int:
            return MAPEO_ANTENAS.get(ant_1based, ant_1based)
        ultimo_ant_cmd = time.time()
        antena_idx = 0
        antena_para_asignar = _num_antena(ANTENNAS_ACTIVAS[0]) if ANTENNAS_ACTIVAS else 1
        ultima_antena_rotacion = antena_para_asignar
        ROTAR_ANTENA_CADA = 0.5
        
        print("🏊 Iniciando lectura de nadadores...")
        print("=" * 60)
        
        try:
            while self.running:
                if duration and (time.time() - start_time) > duration:
                    break
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    
                    self.buffer.extend(data)
                    
                except socket.timeout:
                    now = time.time()
                    if now - ultimo_ant_cmd >= ROTAR_ANTENA_CADA:
                        ant_num = ANTENNAS_ACTIVAS[antena_idx % n_ant]
                        ant = (ant_num - 1) & 0x03
                        ultima_antena_rotacion = _num_antena(ant_num)
                        self.send_command(0x74, bytes([ant]), reader_id=0x01)
                        print(f"  [Rotación → Antena {ultima_antena_rotacion}]", flush=True)
                        time.sleep(0.08)
                        self.send_command(0x89, b'\xFF', reader_id=0x01)
                        antena_idx += 1
                        ultimo_ant_cmd = now
                    continue
                
                while len(self.buffer) > 1:
                    if self.buffer[0] != self.HEADER:
                        self.buffer.pop(0)
                        continue
                    
                    if len(self.buffer) < 2:
                        break
                    data_len = self.buffer[1]
                    frame_len = data_len + 2
                    if len(self.buffer) < frame_len:
                        break
                    frame = bytes(self.buffer[:frame_len])
                    self.buffer = self.buffer[frame_len:]
                    
                    parsed = self.parse_frame(frame)
                    if not parsed:
                        continue
                    tag = None
                    if parsed['cmd'] in [0x89, 0x8B, 0x8A]:  # Inventario
                        tag = self.parse_inventory_tag(parsed['data'], parsed['cmd'])
                    elif parsed['cmd'] in [0x90, 0x91]:  # Buffer
                        tag = self.parse_buffer_tag(parsed['data'])
                    
                    if tag:
                        tag.antenna = antena_para_asignar
                        antena_para_asignar = ultima_antena_rotacion
                        print(tag)
                        if callback:
                            callback(tag)
        
        except KeyboardInterrupt:
            print("\n⏹ Detenido por usuario")
        except Exception as e:
            print(f"\n✗ Error: {e}")
        finally:
            self.running = False


class CompetenciaManager:
    """Orden de llegada; punto cero con iniciar_carrera()."""

    def __init__(self):
        self.llegadas: List[Tuple[int, RFIDTag]] = []
        self.tags_registrados = set()
        self.posicion_actual = 1
        self.hora_inicio: Optional[datetime] = None

    def iniciar_carrera(self):
        self.hora_inicio = datetime.now()
        print(f"⏱ Punto cero fijado: {self.hora_inicio.strftime('%H:%M:%S.%f')[:-3]}\n")

    def _tiempo_carrera(self, tag: RFIDTag) -> Optional[float]:
        if self.hora_inicio is None:
            return None
        return (tag.timestamp - self.hora_inicio).total_seconds()

    def registrar_llegada(self, tag: RFIDTag):
        """Primera detección por EPC; ignora EPCs no válidos (ej. 000000)."""
        if not es_epc_valido(tag.epc):
            return
        if tag.epc not in self.tags_registrados:
            self.llegadas.append((self.posicion_actual, tag))
            self.tags_registrados.add(tag.epc)

            tiempo_str = tag.timestamp.strftime('%H:%M:%S.%f')[:-3]
            elapsed = self._tiempo_carrera(tag)
            if elapsed is not None:
                print(f"🥇 POSICIÓN {self.posicion_actual}: EPC={tag.epc} | Antena={tag.antenna} | Llegada: {tiempo_str} | Tiempo carrera: {elapsed:.3f} s")
            else:
                print(f"🥇 POSICIÓN {self.posicion_actual}: EPC={tag.epc} | Antena={tag.antenna} | {tiempo_str}")
            self.posicion_actual += 1

    def obtener_resultados(self) -> List[dict]:
        return [
            {
                'posicion': pos,
                'epc': tag.epc,
                'timestamp': tag.timestamp.isoformat(),
                'tiempo_carrera_s': self._tiempo_carrera(tag),
                'rssi': tag.rssi,
                'antenna': tag.antenna
            }
            for pos, tag in self.llegadas
        ]

    def guardar_resultados(self, nombre_base: str = 'resultados_nadadores'):
        filename_csv = f"{nombre_base}.csv"

        with open(filename_csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            if self.hora_inicio:
                w.writerow(["inicio_punto_cero", self.hora_inicio.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]])
            w.writerow(["posicion", "epc", "hora_llegada", "tiempo_carrera_s", "antena", "rssi"])
            for pos, tag in self.llegadas:
                elapsed = self._tiempo_carrera(tag)
                w.writerow([
                    pos,
                    tag.epc,
                    tag.timestamp.strftime('%H:%M:%S.%f')[:-3],
                    f"{elapsed:.3f}" if elapsed is not None else "",
                    tag.antenna,
                    tag.rssi
                ])

        print(f"\n💾 Resultados guardados en {filename_csv}")
        try:
            from cruzar_resultados import cruzar_resultados, SALIDA_CSV
            if cruzar_resultados(resultados_csv=filename_csv, salida_csv=SALIDA_CSV):
                print(f"   Cruce con planilla → {SALIDA_CSV}")
        except Exception:
            pass


if __name__ == "__main__":
    from config import LECTOR_IP, LECTOR_PORT
    reader = RFIDReader(LECTOR_IP, LECTOR_PORT)
    competencia = CompetenciaManager()
    if not reader.connect():
        exit(1)
    reader.socket.settimeout(0.5)
    input("Pulsa Enter para iniciar la carrera (punto cero)... ")
    competencia.iniciar_carrera()
    print("Ctrl+C para finalizar y guardar.\n")
    try:
        reader.read_tags_continuous(callback=competencia.registrar_llegada, duration=None)
    finally:
        reader.disconnect()
        competencia.guardar_resultados()
        print("\n" + "=" * 60)
        print(f"Total nadadores: {len(competencia.llegadas)}")
