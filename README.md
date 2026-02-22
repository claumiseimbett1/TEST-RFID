# Sistema de Control RFID para Nadadores

Software para el control y registro de tiempos en natación usando tecnología **RFID UHF** con el lector **R300 YRM200** (RFID reader module).

## Hardware

- **Lector:** **R300 YRM200** – Módulo lector RFID UHF.
- Comunicación con el lector vía **TCP/IP** (protocolo estándar del equipo).

## Protocolo de Comunicación

**Formato de trama:**
```
[0xA0][Len][ReaderId][Cmd][Data...][Checksum]
```

**Comandos principales:**
- `0x89, 0x8B, 0x8A` → Inventario en tiempo real
- `0x90, 0x91` → Tags desde buffer

**Estructura del Tag (Inventario):**
```
[FreqAnt][PC(2bytes)][EPC(N bytes)][RSSI]
```

**Extracción de datos:**
- **EPC**: Identificador único del tag en hexadecimal. En este equipo los EPC tienen **24 caracteres** (12 bytes).
- **Antena**: Calculada de FreqAnt + RSSI_H bit
- **RSSI**: Potencia de señal (convertido a dBm)
- **Timestamp**: Momento de detección

---

## Archivos del proyecto

### 1. `test_conexion.py` – Prueba de conexión

Verifica la conexión TCP/IP con el lector y muestra los datos recibidos (como texto o en hexadecimal). Si la trama empieza con `0xA0`, muestra un resumen (longitud, comando). Útil para comprobar red, formato y etiquetas RFID.

**Uso:**
```bash
python test_conexion.py
```

Edita `LECTOR_IP` y `LECTOR_PORT` al inicio del archivo (por defecto: 192.168.0.178, 4001). Detener con **Ctrl+C**.

---

### 2. `rfid_nadadores.py` – Sistema completo

Sistema con clases para gestión de competencia:

**Clases principales:**
- `RFIDReader`: Maneja conexión TCP y parseo de tramas
- `RFIDTag`: Representa un tag detectado
- `CompetenciaManager`: Registra orden de llegada

**Características:**
- Parsea tramas según protocolo R300 YRM200
- Extrae EPC, antena, RSSI, timestamp
- Registra solo primera detección (evita duplicados)
- Guarda resultados en archivo
- Muestra llegadas en tiempo real

**Uso básico:**
```python
from rfid_nadadores import RFIDReader, CompetenciaManager

reader = RFIDReader("192.168.1.100", 6000)
competencia = CompetenciaManager()

if reader.connect():
    reader.socket.settimeout(0.5)
    reader.read_tags_continuous(
        callback=competencia.registrar_llegada,
        duration=None  # None = infinito
    )
    reader.disconnect()
    competencia.guardar_resultados()
```

---

## Configuración del lector

Antes de usar los scripts:

1. **Configurar IP del lector**: Usa el software del fabricante o configura IP estática (ej. 192.168.0.x con máscara 255.255.255.0).
2. **Puerto TCP**: Según el script (p. ej. 4001 en RFID_TCPIP-test, 6000 en rfid_nadadores).
3. **Modo de operación**: Debe estar en modo inventario continuo enviando datos por TCP.

| Parámetro | Valor ejemplo | Descripción        |
|----------|----------------|--------------------|
| **HOST** | 192.168.0.178  | IP del lector R300 YRM200 |
| **PORT** | 4001 / 6000    | Puerto TCP del lector |

---

## Requisitos e instalación

- **Python 3** (3.6+). Solo biblioteca estándar, sin dependencias externas.
- PC en la misma red que el lector.

```bash
python --version  # Verificar Python 3.6+
```

---

## Flujo de trabajo para competencia

1. Conectar el lector y verificar red.
2. Ejecutar `test_conexion.py` para confirmar comunicación.
3. Ver datos en hex y confirmar que llegan tramas (0xA0).
4. Ejecutar `rfid_nadadores.py` con IP correcta (o integrar en tu aplicación).
5. Los nadadores pasan por las antenas.
6. El sistema registra automáticamente el orden.
7. Presionar **Ctrl+C** para detener.
8. Revisar archivo `resultados_nadadores.txt`.

---

## Interpretación de resultados

**Salida en pantalla:**
```
🥇 POSICIÓN 1: EPC=E28011900000000000000001 | Antena=1 | 14:23:45.123
🥇 POSICIÓN 2: EPC=E28011910000000000000002 | Antena=2 | 14:23:46.789
```

**Archivo generado:**
```
RESULTADOS DE COMPETENCIA
============================================================
1. EPC: E28011900000000000000001 | Tiempo: 14:23:45.123456 | Antena: 1
2. EPC: E28011910000000000000002 | Tiempo: 14:23:46.789012 | Antena: 2
```

---

## Notas importantes

- **Antenas múltiples**: Si usas varias antenas, configura cuál está en la línea de meta.
- **RSSI**: Valor negativo en dBm (ej: -50 dBm = señal fuerte).
- **Duplicados**: El sistema filtra automáticamente re-lecturas del mismo tag.
- **Sincronización**: Usa NTP en tu PC para timestamps precisos.

---

## Troubleshooting

**No se conecta:**
- Verifica IP/puerto con ping o telnet.
- Revisa firewall del PC.
- Confirma que el lector está encendido.

**Recibe datos pero no parsea:**
- Ejecuta `test_conexion.py` y revisa los hex.
- Verifica que la trama empieza con `0xA0`.
- Puede ser variante de protocolo.

**Tags no detectados:**
- Verifica que el lector está en modo inventario.
- Revisa potencia de antenas.
- Confirma que los tags son compatibles UHF.

---

## Personalización

**Cambiar lógica de registro** (en `CompetenciaManager.registrar_llegada()`):
- Filtrado por antena específica.
- Tiempo mínimo entre detecciones.
- Validación de EPCs conocidos.

**Múltiples antenas por carril:**
```python
CARRILES = {
    1: "Carril 1",
    2: "Carril 2",
    # ...
}
```

---

## Próximos pasos

- Interpretar el formato de datos del R300 YRM200 (EPC, tiempos, etc.) según necesidad.
- Integrar la lectura en la aplicación final de **manejo de tiempos en natación**.

---

## Referencias

- SDK: Carpeta `Demo/UHFDemo_v4.2_EN_SRC/Reader/`
- Protocolo: Ver `MessageTran.cs` y `Tag.cs`
- Manual: documentación del fabricante del R300 YRM200
