# Sistema de Control RFID para Nadadores

Software para el control y registro de tiempos en natación usando **RFID UHF** con el lector **R300 YRM200** (RFID reader module). Conexión por TCP/IP; el tiempo de cada nadador se calcula desde un **punto cero** que tú defines (inicio de carrera).

**Salidas:** Se usa **CSV** para resultados y planillas (Excel, cruce) y **JSON** para backup con metadata. El único **TXT** es la lista de EPCs para el writer (`epcs_para_writer.txt`), que muchos equipos esperan en ese formato.

**Resumen rápido:**
- **`test_conexion.py`**: Prueba de conexión al lector; muestra datos [TEXTO]/[HEX].
- **`rfid_nadadores.py`**: Registra llegadas por EPC y **exporta en CSV** (`resultados_nadadores.csv`). Si existe `tags_para_registro.csv`, genera **`resultados_con_nadadores.csv`** (con nombre si hay `nombres_nadadores.csv`).
- **`cruzar_resultados.py`**: Cruza resultados con la planilla y opcionalmente con `nombres_nadadores.csv`; salida en **CSV**.
- **`generar_epcs.py`**: Generador de EPCs; exporta **CSV** (planilla), **JSON** (backup) y **TXT** solo para el writer (lista de EPCs). Ver **README_EPC_GENERATION.md**.

## Hardware

- **Lector:** R300 YRM200 – Módulo lector RFID UHF.
- **Comunicación:** TCP/IP. El programa del SDK/lector envía el flujo de tags por red; esta aplicación se conecta como cliente y recibe los datos. El punto cero (inicio de carrera) se define **en esta aplicación**, no en el SDK.

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

### `config.py` – Configuración del lector

Define **`LECTOR_IP`** y **`LECTOR_PORT`** en un solo lugar. Usado por `test_conexion.py` y `rfid_nadadores.py`. Edita aquí la IP y el puerto de tu R300 YRM200 (por defecto: 192.168.0.178, 4001).

---

### `test_conexion.py` – Prueba de conexión

Verifica la conexión TCP/IP con el lector y muestra los datos recibidos. Cada línea se etiqueta como **[TEXTO]** o **[HEX]**; si la trama empieza con `0xA0`, muestra un resumen (Len, ReaderId, Cmd). Útil para comprobar red y que lleguen tags.

**Uso:**
```bash
python test_conexion.py
```

Detener con **Ctrl+C**. La IP y el puerto se leen de `config.py`.

---

### `rfid_nadadores.py` – Sistema completo

Sistema con clases para gestión de competencia y **cálculo del tiempo de carrera** desde un punto cero.

**Clases principales:**
- **RFIDReader**: Conexión TCP y parseo de tramas del R300 YRM200.
- **RFIDTag**: Tag detectado (EPC, RSSI, antena, timestamp).
- **CompetenciaManager**: Orden de llegada, **punto cero** e **inicio de carrera**.

**CompetenciaManager – Punto cero y tiempo de carrera:**
- **`iniciar_carrera()`**: Fija el momento de inicio (punto cero). A partir de ahí, el tiempo de cada nadador es *timestamp del tag − punto cero*.
- Si no llamas a `iniciar_carrera()`, solo se muestra la hora de llegada; si la llamas, además se muestra **Tiempo carrera: X.XXX s** en pantalla y en el archivo de resultados.

**Características:**
- Parsea tramas según protocolo R300 YRM200.
- Extrae EPC (24 caracteres), antena, RSSI, timestamp.
- Registra solo la primera detección de cada EPC (evita duplicados).
- Guarda resultados en **CSV** (mismo nombre base): hora de llegada y, si hay punto cero, tiempo de carrera en segundos.
- Al ejecutar como script, pide **Enter para iniciar la carrera** y luego lee tags hasta Ctrl+C.

**Uso desde consola:**
```bash
python rfid_nadadores.py
```
1. Conecta al lector.
2. Pulsa **Enter** para marcar el inicio de la carrera (punto cero).
3. Los nadadores pasan por las antenas; se muestra posición, EPC, hora de llegada y tiempo de carrera.
4. **Ctrl+C** para detener; se guarda `resultados_nadadores.csv`. Si existe `tags_para_registro.csv`, se genera también `resultados_con_nadadores.csv` (cruce automático).

**Uso programático:**
```python
from config import LECTOR_IP, LECTOR_PORT
from rfid_nadadores import RFIDReader, CompetenciaManager

reader = RFIDReader(LECTOR_IP, LECTOR_PORT)
competencia = CompetenciaManager()

if reader.connect():
    reader.socket.settimeout(0.5)
    # Definir punto cero (ej. al dar la salida)
    competencia.iniciar_carrera()
    reader.read_tags_continuous(
        callback=competencia.registrar_llegada,
        duration=None
    )
    reader.disconnect()
    competencia.guardar_resultados()
```

---

### `cruzar_resultados.py` – Cruce EPC → nadador (con nombre opcional)

Cruza los resultados de la carrera con la planilla de EPCs y genera **`resultados_con_nadadores.csv`** con: posición, EPC, **nombre** (opcional), número corredor, categoría, género, distancia, hora llegada, tiempo carrera, antena, rssi, edades.

- **Planilla**: `tags_para_registro.csv` (de generar_epcs) — obligatoria para el cruce.
- **Nombres (opcional)**: Si existe **`nombres_nadadores.csv`** con columnas `epc` y `nombre`, cada EPC se asocia al nombre del nadador y se incluye en la columna **nombre** del CSV de salida. Así puedes cargar un listado EPC → nombre (ej. inscritos) y que el cruce lo use.
- **Integrado**: Al guardar resultados, `rfid_nadadores.py` ejecuta el cruce si existe `tags_para_registro.csv`; si además existe `nombres_nadadores.csv`, la salida incluye el nombre.
- **Manual**: `python cruzar_resultados.py`.

**Formato `nombres_nadadores.csv`:**
```csv
epc,nombre
E28011900000000000000001,María García
E28011910000000000000002,Carlos López
```
EPC puede ir con o sin espacios; se normaliza al cruzar.

---

## Configuración del lector

1. **IP del lector**: Configuración del fabricante o IP estática (ej. 192.168.0.x). Ponla en `config.py` como `LECTOR_IP`.
2. **Puerto TCP**: Por defecto 4001 en `config.py` (`LECTOR_PORT`). Algunos equipos usan 6000.
3. **Modo**: El lector/SDK debe estar enviando datos por TCP (modo inventario continuo o equivalente).

| Parámetro   | Ejemplo       | Descripción           |
|------------|---------------|------------------------|
| LECTOR_IP  | 192.168.0.178 | IP del R300 YRM200     |
| LECTOR_PORT| 4001          | Puerto TCP del lector |

---

## Requisitos

- **Python 3** (3.6+). Solo biblioteca estándar.
- PC en la misma red que el lector.

```bash
python --version  # Verificar 3.6+
```

---

## Flujo de trabajo para competencia

1. Ajusta `LECTOR_IP` y `LECTOR_PORT` en `config.py`.
2. Comprueba conexión: `python test_conexion.py` (debes ver [TEXTO] o [HEX] al pasar tags). Ctrl+C para salir.
3. Ejecuta `python rfid_nadadores.py`.
4. Cuando estés listo (p. ej. al dar la salida), **pulsa Enter** para marcar el punto cero.
5. Los nadadores pasan por las antenas; se registran posición, EPC, hora de llegada y tiempo de carrera.
6. **Ctrl+C** para finalizar; se guarda `resultados_nadadores.csv`. Si existe `tags_para_registro.csv`, se genera también **`resultados_con_nadadores.csv`** (con nombre si existe `nombres_nadadores.csv`).
7. Revisa los archivos. Para ver **qué nadador es** cada EPC: usa `resultados_con_nadadores.csv` (cruce con la planilla) o ejecuta `python cruzar_resultados.py` a mano.

---

## Interpretación de resultados

**En pantalla (con punto cero):**
```
⏱ Punto cero fijado: 14:23:12.667

🥇 POSICIÓN 1: EPC=E28011900000000000000001 | Antena=1 | Llegada: 14:23:45.123 | Tiempo carrera: 32.456 s
🥇 POSICIÓN 2: EPC=E28011910000000000000002 | Antena=2 | Llegada: 14:23:46.789 | Tiempo carrera: 34.122 s
```

**Archivo `resultados_nadadores.csv`:**
```csv
inicio_punto_cero,2025-02-22 14:23:12.667
posicion,epc,hora_llegada,tiempo_carrera_s,antena,rssi
1,E28011900000000000000001,14:23:45.123,32.456,1,-50
2,E28011910000000000000002,14:23:46.789,34.122,2,-48
```

**Archivo `resultados_con_nadadores.csv`** (si existe planilla `tags_para_registro.csv`; columna **nombre** si existe `nombres_nadadores.csv`):
```csv
inicio_punto_cero,2025-02-22 14:23:12.667
posicion,epc,nombre,numero_corredor,categoria_nombre,genero,distancia,hora_llegada,tiempo_carrera_s,antena,rssi,edad_min,edad_max
1,E2801190...,María García,1,Infantil A,Femenino,2000,14:23:45.123,32.456,1,-50,8,9
2,E2801191...,Carlos López,2,Juvenil A,Masculino,2000,14:23:46.789,34.122,2,-48,12,13
```
Con este archivo sabes **qué nadador es** cada EPC (nombre, número, categoría, género, distancia). La columna **nombre** se rellena si tienes `nombres_nadadores.csv` (epc, nombre).

El **tiempo de carrera** de cada nadador es el número de segundos desde el punto cero hasta la detección de su tag.

---

## Notas importantes

- **Punto cero**: Lo defines tú (Enter al ejecutar el script, o `competencia.iniciar_carrera()` en código). El SDK del lector solo envía datos por TCP; no tiene concepto de “inicio de carrera”.
- **EPC**: 24 caracteres hexadecimales en este equipo.
- **Antenas**: Si usas varias, define cuál corresponde a la línea de meta.
- **RSSI**: Valor en dBm (negativo; ej. -50 dBm = señal fuerte).
- **Duplicados**: Se ignora la segunda y siguientes detecciones del mismo EPC.
- **Hora**: Usa NTP en el PC para que los tiempos sean coherentes.

---

## Troubleshooting

**No se conecta**
- Comprueba IP y puerto en `config.py`, ping al lector, firewall y que el lector/SDK esté enviando por TCP.

**Recibe datos pero no parsea**
- Ejecuta `test_conexion.py` y revisa si las tramas empiezan por `0xA0`. Puede haber variante de protocolo.

**Tags no detectados**
- Modo inventario activo, potencia de antenas y tags UHF compatibles.

---

## Personalización

- **Registro** (`CompetenciaManager.registrar_llegada`): filtrar por antena, tiempo mínimo entre detecciones, validar EPCs conocidos.
- **Carriles por antena**: mapear número de antena a carril (ej. diccionario `CARRILES = {1: "Carril 1", 2: "Carril 2", ...}`).

---

## Archivos generados (resumen)

| Origen | Archivos |
|--------|----------|
| **rfid_nadadores** | `resultados_nadadores.csv` |
| **rfid_nadadores + planilla** | `resultados_con_nadadores.csv` (EPC, nombre si hay `nombres_nadadores.csv`, número, categoría, género, distancia, tiempos) |
| **cruzar_resultados** | `resultados_con_nadadores.csv` (mismo; opcionalmente usa `nombres_nadadores.csv`) |
| **generar_epcs** | `tags_para_registro.csv`, `tags_completo.json`, `epcs_para_writer.txt` (solo lista de EPCs para el writer) |

---

## Otros programas del proyecto

- **Generador de EPCs** (`generar_epcs.py`): Crea códigos EPC por categoría/género/distancia para programar tags. Exporta **TXT**, **CSV** y **JSON**. Ver **README_EPC_GENERATION.md**.
- **Cruce de resultados** (`cruzar_resultados.py`): Cruce resultados de carrera con planilla de EPCs; se ejecuta solo o desde rfid_nadadores al guardar.

---

## Referencias

- SDK del equipo (Demo/lector del fabricante).
- Manual: documentación del fabricante del R300 YRM200.
