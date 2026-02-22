# Sistema de manejo de tiempos en natación con RFID

Software para el control y registro de tiempos en natación usando tecnología **RFID UHF**.

## Hardware

- **Lector:** YR8700 con **Impinj R2000**, 4 puertos UHF RFID.
- Comunicación con el lector vía **TCP/IP** (protocolo estándar del equipo).

## Fase actual: lectura de datos por TCP/IP

Antes de integrar el lector en la aplicación de tiempos, se usa un programa de prueba que **solo lee y muestra** los datos que envía el lector por red.

### Programa: `testRFID-serialPort.py`

- Se conecta al lector por **TCP/IP** (cliente).
- Muestra en consola los datos recibidos **tal como llegan** (texto o hex si no es texto).
- Sirve para comprobar conectividad, formato de datos y etiquetas RFID leídas.

### Requisitos

- Python 3 (solo biblioteca estándar, sin dependencias externas).
- PC en la misma red que el lector (ej. 192.168.0.x con máscara 255.255.255.0).

### Configuración del lector

En el script se usan por defecto:

| Parámetro | Valor   | Descripción        |
|----------|--------|--------------------|
| **HOST** | 192.168.0.178 | IP del lector YR8700 |
| **PORT** | 4001   | Puerto TCP del lector |

Ajusta `HOST` y `PORT` en `testRFID-serialPort.py` si tu lector tiene otra IP o puerto.

### Uso

1. Configura el lector en la red (IP, máscara, puerto).
2. Ejecuta:
   ```bash
   python testRFID-serialPort.py
   ```
3. Acerca etiquetas RFID al lector; los datos aparecerán en la consola.
4. Salir con **Ctrl+C**.

### Próximos pasos

- Interpretar el formato de datos del R2000 (EPC, tiempos, etc.).
- Integrar esta lectura en la aplicación de **manejo de tiempos en natación**.
