#!/usr/bin/env python3
"""
Lector RFID para control de nadadores - R300 YRM200 (RFID reader module)
Protocolo: Tramas binarias 0xA0 [Len] [ReaderId] [Cmd] [Data] [Checksum]
"""
import csv
import socket
import struct
from datetime import datetime
from typing import Optional, List, Tuple
import time


# EPC en este equipo: 24 caracteres hex (12 bytes)
EPC_LEN_HEX = 24


class RFIDTag:
    """Representa un tag RFID detectado (EPC de 24 caracteres hex)."""
    def __init__(self, epc: bytes, rssi: int, antenna: int, timestamp: datetime):
        self.epc = epc.hex().upper()  # EPC en hexadecimal (24 chars en R300 YRM200)
        self.rssi = rssi - 129  # Convertir a dBm
        self.antenna = antenna
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"Tag(EPC={self.epc}, RSSI={self.rssi}dBm, Ant={self.antenna}, Time={self.timestamp.strftime('%H:%M:%S.%f')[:-3]})"


class RFIDReader:
    """Cliente TCP para lector RFID R300 YRM200"""
    
    HEADER = 0xA0
    CMD_INVENTORY = 0x89  # Comando de respuesta de inventario en tiempo real
    CMD_BUFFER = 0x90     # Comando de respuesta de buffer
    
    def __init__(self, ip: str, port: int = 6000):
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.buffer = bytearray()
        self.running = False
        
    def connect(self) -> bool:
        """Conectar al lector RFID"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            print(f"✓ Conectado a {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False
    
    def disconnect(self):
        """Desconectar del lector"""
        self.running = False
        if self.socket:
            self.socket.close()
            print("✓ Desconectado")
    
    @staticmethod
    def checksum(data: bytes) -> int:
        """Calcular checksum (XOR de todos los bytes)"""
        return sum(data) & 0xFF
    
    def send_command(self, cmd: int, data: bytes = b'', reader_id: int = 0xFF):
        """Enviar comando al lector"""
        data_len = len(data) + 3  # ReaderId + Cmd + Data
        frame = struct.pack('BBB', self.HEADER, data_len, reader_id)
        frame += struct.pack('B', cmd) + data
        frame += struct.pack('B', self.checksum(frame))
        
        self.socket.send(frame)
    
    def parse_frame(self, frame: bytes) -> Optional[dict]:
        """Parsear trama recibida"""
        if len(frame) < 5 or frame[0] != self.HEADER:
            return None
        
        # Validar checksum
        if self.checksum(frame[:-1]) != frame[-1]:
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
        """
        Parsear tag de inventario en tiempo real
        Formato: [FreqAnt][PC(2)][EPC(N)][Rssi]
        """
        if len(data) < 5:  # Mínimo: FreqAnt + PC + EPC(1byte) + Rssi
            return None
        
        idx = 0
        freq_ant = data[idx]
        idx += 1
        
        # PC (2 bytes)
        pc = data[idx:idx+2]
        idx += 2
        
        # EPC (resto menos RSSI)
        epc_len = len(data) - idx - 1
        epc = data[idx:idx+epc_len]
        idx += epc_len
        
        # RSSI
        rssi_raw = data[idx]
        
        # Extraer antena y frecuencia
        freq = (freq_ant & 0xFC) >> 2
        ant_no = (freq_ant & 0x03)
        
        rssi_h = (rssi_raw & 0x80) >> 7
        rssi = rssi_raw & 0x7F
        
        # Calcular número de antena real (1-8)
        antenna = ant_no + (4 if rssi_h == 1 else 0) + 1
        
        return RFIDTag(epc, rssi, antenna, datetime.now())
    
    def parse_buffer_tag(self, data: bytes) -> Optional[RFIDTag]:
        """
        Parsear tag del buffer
        Formato: [TagCount(2)][DataLen][PC(2)][EPC(N)][CRC(2)][Rssi][FreqAnt][ReadCount]
        """
        if len(data) < 9:
            return None
        
        idx = 0
        tag_count = struct.unpack('>H', data[idx:idx+2])[0]  # Big endian
        idx += 2
        
        data_len = data[idx]
        idx += 1
        
        # PC (2 bytes)
        pc = data[idx:idx+2]
        idx += 2
        
        # EPC (DataLen - PC - CRC)
        epc_len = data_len - 4
        epc = data[idx:idx+epc_len]
        idx += epc_len
        
        # CRC (2 bytes)
        crc = data[idx:idx+2]
        idx += 2
        
        # RSSI
        rssi_raw = data[idx]
        idx += 1
        
        # FreqAnt
        freq_ant = data[idx]
        idx += 1
        
        # ReadCount
        read_count = data[idx]
        
        # Calcular antena
        freq = (freq_ant & 0xFC) >> 2
        ant_no = freq_ant & 0x03
        
        rssi_h = (rssi_raw & 0x80) >> 7
        rssi = rssi_raw & 0x7F
        
        antenna = ant_no + (4 if rssi_h == 1 else 0) + 1
        
        return RFIDTag(epc, rssi, antenna, datetime.now())
    
    def read_tags_continuous(self, callback=None, duration: int = None):
        """
        Leer tags continuamente
        callback: función que recibe RFIDTag cuando se detecta
        duration: segundos de lectura (None = infinito)
        """
        self.running = True
        start_time = time.time()
        
        print("🏊 Iniciando lectura de nadadores...")
        print("=" * 60)
        
        try:
            while self.running:
                # Verificar tiempo límite
                if duration and (time.time() - start_time) > duration:
                    break
                
                # Leer datos del socket
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    
                    self.buffer.extend(data)
                    
                except socket.timeout:
                    continue
                
                # Procesar buffer buscando tramas completas (0xA0)
                while len(self.buffer) > 1:
                    # Buscar inicio de trama
                    if self.buffer[0] != self.HEADER:
                        self.buffer.pop(0)
                        continue
                    
                    # Verificar si tenemos trama completa
                    if len(self.buffer) < 2:
                        break
                    
                    data_len = self.buffer[1]
                    frame_len = data_len + 2  # Header + Len + Data + Checksum
                    
                    if len(self.buffer) < frame_len:
                        break  # Esperar más datos
                    
                    # Extraer trama completa
                    frame = bytes(self.buffer[:frame_len])
                    self.buffer = self.buffer[frame_len:]
                    
                    # Parsear trama
                    parsed = self.parse_frame(frame)
                    if not parsed:
                        continue
                    
                    # Parsear tag según comando
                    tag = None
                    if parsed['cmd'] in [0x89, 0x8B, 0x8A]:  # Inventario
                        tag = self.parse_inventory_tag(parsed['data'], parsed['cmd'])
                    elif parsed['cmd'] in [0x90, 0x91]:  # Buffer
                        tag = self.parse_buffer_tag(parsed['data'])
                    
                    # Notificar tag detectado
                    if tag:
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
    """Gestiona el orden de llegada de nadadores. El punto cero (inicio de carrera) se define con iniciar_carrera()."""

    def __init__(self):
        self.llegadas: List[Tuple[int, RFIDTag]] = []  # (posición, tag)
        self.tags_registrados = set()  # EPCs ya registrados
        self.posicion_actual = 1
        self.hora_inicio: Optional[datetime] = None  # Punto cero; None = no definido

    def iniciar_carrera(self):
        """Define el punto cero: desde este momento se calcula el tiempo de carrera de cada nadador."""
        self.hora_inicio = datetime.now()
        print(f"⏱ Punto cero fijado: {self.hora_inicio.strftime('%H:%M:%S.%f')[:-3]}\n")

    def _tiempo_carrera(self, tag: RFIDTag) -> Optional[float]:
        """Segundos desde hora_inicio hasta el tag. None si no hay punto cero."""
        if self.hora_inicio is None:
            return None
        return (tag.timestamp - self.hora_inicio).total_seconds()

    def registrar_llegada(self, tag: RFIDTag):
        """Registra la llegada de un nadador (solo primera detección)"""
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
        """Retorna lista de resultados ordenados"""
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
        """Guarda resultados en CSV (mismo nombre base)."""
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

        # Cruce con planilla de EPCs (tags_para_registro.csv) si existe
        try:
            from cruzar_resultados import cruzar_resultados, PLANILLA_CSV, SALIDA_CSV
            if cruzar_resultados(resultados_csv=filename_csv, salida_csv=SALIDA_CSV):
                print(f"   Cruce con planilla → {SALIDA_CSV} (EPC + número corredor, categoría, género, distancia)")
        except Exception:
            pass


# Ejemplo de uso
if __name__ == "__main__":
    from config import LECTOR_IP, LECTOR_PORT

    # Crear lector y gestor de competencia
    reader = RFIDReader(LECTOR_IP, LECTOR_PORT)
    competencia = CompetenciaManager()

    # Conectar
    if not reader.connect():
        exit(1)

    # Socket no bloqueante con timeout
    reader.socket.settimeout(0.5)

    # Punto cero: el usuario define cuándo empieza la carrera
    input("Pulsa Enter para iniciar la carrera (punto cero)... ")
    competencia.iniciar_carrera()

    try:
        # Leer tags y registrar llegadas
        reader.read_tags_continuous(
            callback=competencia.registrar_llegada,
            duration=None  # None = infinito, o especificar segundos
        )
    finally:
        reader.disconnect()
        competencia.guardar_resultados()

        # Mostrar resumen
        print("\n" + "=" * 60)
        print(f"Total nadadores registrados: {len(competencia.llegadas)}")
