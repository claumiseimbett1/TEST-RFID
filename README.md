# Sistema de Control RFID para Nadadores

Software para el control y registro de tiempos en natación usando **RFID UHF** con el lector **R300 YRM200** (RFID reader module). Conexión por TCP/IP; el tiempo de cada nadador se calcula desde un **punto cero** que tú defines (inicio de carrera).

**Salidas:** Se usa **CSV** para resultados y planillas (Excel, cruce) y **JSON** para backup con metadata. El único **TXT** es la lista de EPCs para el writer (`epcs_para_writer.txt`), que muchos equipos esperan en ese formato.

**Resumen rápido:**
- **`test_conexion.py`**: Prueba de conexión al lector. Configura potencia 30 dBm, rota solo las antenas configuradas en `ANTENNAS_ACTIVAS` (ej. 3 y 4) cada 0,5 s y envía inventario (0x89 + 0x80/0x90). Muestra **"Tag leído: EPC=... Ant=X RSSI=X dBm"**. Útil para comprobar que el lector lee antes de la carrera.
- **`rfid_nadadores.py`**: Registra llegadas por EPC (ignora EPCs no válidos como 000000) y **exporta en CSV** (`resultados_nadadores.csv`). Asigna la antena correcta por orden de llegada. Si existe `tags_para_registro.csv`, genera **`resultados_con_nadadores.csv`** (con nombre si hay `nombres_nadadores.csv`).
- **`cruzar_resultados.py`**: Cruza resultados con la planilla y con `nombres_nadadores.csv` (nombres por EPC). Soporta CSV en UTF-8, cp1252 o latin-1. Normaliza EPC (espacios, prefijo 00). Salida en **CSV**.
- **`generar_epcs.py`**: Generador de EPCs; defines distancias y femeninos/masculinos por categoría. Exporta **CSV**, **JSON**, **TXT** para el writer y **PDF** con reporte de totales. Ver **README_EPC_GENERATION.md**.

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

| Parámetro | Descripción |
|-----------|-------------|
| `LECTOR_IP` | IP del R300 YRM200 (ej. 192.168.0.178). |
| `LECTOR_PORT` | Puerto TCP (4001 o 6000 según el equipo). |
| `SKIP_CHECKSUM` | Si el lector usa otro checksum, pon `True` para no validarlo. |
| `SEND_START_INVENTORY` | `True` = enviar al conectar comandos de inventario (0x74 antena, 0x76 potencia, 0x89, 0x80/0x90). |
| `NUM_ANTENNAS` | Número de antenas del lector (4 en R300 YRM200). |
| `ANTENNAS_ACTIVAS` | Números de antena 1-4 (puertos del lector): `[1,2,3,4]` = las 4; `[3, 4]` = solo antenas 3 y 4. |
| `MAPEO_ANTENAS` | Diccionario para que lo mostrado coincida con la antena física. `{}` = sin cambio. Si en tu equipo salen al revés: `{3: 4, 4: 3}`. |

---

### `test_conexion.py` – Prueba de conexión

Comprueba que el lector responde y lee tags. **Recomendado ejecutarlo antes de la carrera.**

Al conectar, el script:
1. Fija **potencia RF a 30 dBm** (0x76).
2. Envía **antena de trabajo** (0x74) e **inventario en tiempo real** (0x89 con byte Channel 0xFF).
3. Envía también **inventario a buffer** (0x80) y **lectura del buffer** (0x90).
4. Cada **0,5 s** rota por las antenas definidas en `ANTENNAS_ACTIVAS` (ej. solo 3 y 4) y repite 0x74 + 0x89 + 0x80/0x90.

Cuando el lector detecta un tag, aparece **"Tag leído: EPC=... Ant=X RSSI=X dBm"** (Ant usa la antena de la rotación; el R300 suele reportar siempre 4 en la trama).

**Uso:**
```bash
python test_conexion.py
```
Cierra el SDK del lector antes. Acerca un tag a la antena y espera unos segundos. Detener con **Ctrl+C**.

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
- **Ignora EPCs no válidos** (ej. 000000 o solo ceros) para no registrar falsas llegadas.
- Asigna la **antena correcta** por orden de llegada (la que estaba activa cuando se leyó el tag); usa `MAPEO_ANTENAS` si en tu equipo los números salen al revés.
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

Cruza los resultados de la carrera con la planilla de EPCs y genera **`resultados_con_nadadores.csv`** con: posición, EPC, **nombre** (si existe `nombres_nadadores.csv`), número corredor, categoría, género, distancia, hora llegada, tiempo carrera, antena, rssi, edades y **`epc_en_planilla`** (sí/no).

- **Planilla**: `tags_para_registro.csv` (de generar_epcs) — obligatoria para el cruce.
- **Nombres**: Si existe **`nombres_nadadores.csv`** con columnas `epc` y `nombre`, se cargan los nombres y se muestra "Nombres cargados: N desde nombres_nadadores.csv". La columna **nombre** del CSV de salida se rellena por EPC. Acepta cabeceras con BOM y variantes (EPC, nombre_nadador). Los CSV pueden estar en **UTF-8, cp1252 o latin-1** (p. ej. exportados desde Excel en Windows).
- **Normalización de EPC**: Se quitan espacios; si el EPC tiene más de 24 caracteres hex (ej. prefijo `00` en resultados del lector), se usan los últimos 24 para el cruce, así coinciden con la planilla y con `nombres_nadadores.csv`.
- **Integrado**: Al guardar resultados, `rfid_nadadores.py` ejecuta el cruce si existe `tags_para_registro.csv`.
- **Manual**: `python cruzar_resultados.py`.

**Formato `nombres_nadadores.csv`:**
```csv
epc,nombre
E2 80 07 EA 02 01 01 00 00 01 00 8C,Clara Méndez
E28007EA020502000001008B,Camila Herrera
```
EPC puede ir **con o sin espacios**; se normaliza al cruzar. Si en resultados el EPC viene con prefijo `00` (26 caracteres), se ajusta automáticamente.

---

## Configuración del lector

1. **IP y puerto**: En `config.py` ajusta `LECTOR_IP` y `LECTOR_PORT` (por defecto 4001; algunos R300 usan 6000).
2. **SDK cerrado**: El lector acepta una sola conexión TCP. Cierra el programa del fabricante antes de usar `test_conexion.py` o `rfid_nadadores.py`.
3. **Antenas**: Usa **números de antena 1-4** (puertos del lector). Si solo tienes conectadas las antenas 3 y 4: `ANTENNAS_ACTIVAS = [3, 4]`. Para las 4: `[1, 2, 3, 4]`. La rotación y lo que se guarda en CSV usan solo esas antenas.
4. **Numeración de antena**: Si al pasar por la antena física 3 marca 4 (y al revés), en `config.py` pon `MAPEO_ANTENAS = {3: 4, 4: 3}`. Con `{}` no se cambia.

### Correcciones de protocolo R300 aplicadas

Los scripts ya envían los comandos que exige el protocolo oficial del R300 YRM200:

- **0x89 (inventario en tiempo real)** debe llevar **1 byte Channel** (se envía 0xFF). Sin ese byte el lector no devuelve tags.
- **0x74 (set work antenna)**: Fija la antena de trabajo antes del inventario; sin ello el lector puede no leer.
- **0x76 (set output power)**: Se envía 30 dBm al conectar para mejorar el alcance (rango 20–33 dBm).
- **0x80 + 0x90**: Inventario a buffer y lectura del buffer; en algunos casos el lector responde mejor con esta secuencia.

`test_conexion.py` aplica todo lo anterior y rota por las antenas configuradas en `ANTENNAS_ACTIVAS` cada 0,5 s; cuando lee un tag muestra **"Tag leído: EPC=... Ant=X RSSI=X dBm"**.

**Si no se registran tags:**
1. Cierra el SDK y ejecuta `python test_conexion.py`. Acerca el tag y espera varios segundos (rotación de antenas).
2. Si no aparece "Tag leído", revisa IP/puerto en `config.py`, que el tag sea UHF Gen2 y que la antena esté bien conectada.
3. Si con el SDK sí lee y con Python no, los scripts ya envían 0x74, 0x76, 0x89+Channel y 0x80/0x90; comprueba que usas la misma red y puerto que el SDK.

---

## Requisitos

- **Python 3** (3.6+). Solo biblioteca estándar.
- PC en la misma red que el lector.

```bash
python --version  # Verificar 3.6+
```

---

## Pruebas (tests)

Hay tests unitarios y de integración para el cruce de resultados y el guardado.

**Requisito:** `pytest` (opcional).  
`pip install pytest`

**Ejecutar desde la raíz del proyecto:**

```bash
python -m pytest tests/ -v
```

- **`tests/test_cruzar_resultados.py`**: normalización de EPC, carga de nombres, cruce con planilla, columna `epc_en_planilla` (sí/no), archivos faltantes, uso opcional de `nombres_nadadores.csv`.
- **`tests/test_rfid_nadadores.py`**: `CompetenciaManager` (punto cero, llegadas, duplicados, tiempos), formato del CSV de resultados al guardar.

---

## Flujo de trabajo para competencia

1. Ajusta `LECTOR_IP`, `LECTOR_PORT` y, si aplica, `ANTENNAS_ACTIVAS` en `config.py`.
2. Comprueba que el lector lee: `python test_conexion.py`. Acerca un tag y verifica que aparezca **"Tag leído: EPC=..."**. Ctrl+C para salir.
3. Cierra el SDK y ejecuta `python rfid_nadadores.py`.
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

**Archivo `resultados_con_nadadores.csv`** (si existe planilla `tags_para_registro.csv`; columna **nombre** si existe `nombres_nadadores.csv`; columna **epc_en_planilla** para validar si el EPC está en la planilla: sí/no):
```csv
inicio_punto_cero,2025-02-22 14:23:12.667
posicion,epc,nombre,numero_corredor,categoria_nombre,genero,distancia,hora_llegada,tiempo_carrera_s,antena,rssi,edad_min,edad_max,epc_en_planilla
1,E2801190...,María García,1,Infantil A,Femenino,2000,14:23:45.123,32.456,1,-50,8,9,sí
2,E2801191...,Carlos López,2,Juvenil A,Masculino,2000,14:23:46.789,34.122,2,-48,12,13,sí
```
Con este archivo sabes **qué nadador es** cada EPC (nombre, número, categoría, género, distancia). La columna **nombre** se rellena si tienes `nombres_nadadores.csv` (epc, nombre). Si en una misma salida compites **varias distancias** (p. ej. 2K y 3K) con el **mismo punto cero**, todas las llegadas quedan en este CSV; puedes separar por carrera **filtrando por la columna `distancia`** en Excel (cada EPC ya trae su distancia en la planilla).

El **tiempo de carrera** de cada nadador es el número de segundos desde el punto cero hasta la detección de su tag.

---

## Notas importantes

- **Punto cero**: Lo defines tú (Enter al ejecutar el script, o `competencia.iniciar_carrera()` en código). El SDK del lector solo envía datos por TCP; no tiene concepto de “inicio de carrera”.
- **EPC**: 24 caracteres hexadecimales en este equipo. Se ignoran EPCs no válidos (ej. 000000).
- **Antenas**: Configura solo las que tengas conectadas (`ANTENNAS_ACTIVAS`). Usa `MAPEO_ANTENAS` si la numeración no coincide con los puertos físicos.
- **RSSI**: Valor en dBm (negativo; ej. -50 dBm = señal fuerte).
- **Duplicados**: Se ignora la segunda y siguientes detecciones del mismo EPC.
- **Hora**: Usa NTP en el PC para que los tiempos sean coherentes.
- **Varias distancias en un registro**: Puedes tener varias carreras (p. ej. 2K y 3K) con el **mismo punto cero** en una sola sesión; el EPC incluye la distancia. En `resultados_con_nadadores.csv` la columna **distancia** permite filtrar por carrera.
- **Un solo evento**: El sistema está pensado para **un evento por sesión**: un único punto cero (hora de salida). Varias distancias comparten ese mismo inicio y se separan por la columna `distancia` en el CSV.
- **Ampliación futura (varios eventos)**: Se podría extender para manejar varios eventos en la misma jornada: cada evento tendría su propio punto cero (hora de salida) y en el EPC ya existe un campo (`prefijo_evento` en el generador, codificado en el EPC) que podría usarse como identificador de evento. Así, cada tag indicaría a qué evento pertenece y el programa podría asignar el tiempo de carrera usando el punto cero correspondiente a ese evento. No está implementado en la versión actual.

---

## Troubleshooting

**No se conecta**
- Comprueba IP y puerto en `config.py`, ping al lector, firewall. Cierra el SDK (solo una conexión TCP).

**Recibe datos pero no aparece "Tag leído"**
- `test_conexion.py` ya envía 0x74 (antena), 0x76 (30 dBm), 0x89+Channel y 0x80/0x90. Acerca el tag a la antena y espera varias rondas (rotación 4 antenas). Revisa que el tag sea UHF Gen2 y la región de frecuencia (FCC/ETSI) correcta.

**Tags no detectados en carrera (`rfid_nadadores.py`)**
- Misma configuración que en test: potencia, `ANTENNAS_ACTIVAS` en `config.py`. Asegura que antes de la carrera `test_conexion.py` sí mostró "Tag leído" con ese tag.

**Nombres no aparecen en resultados_con_nadadores.csv**
- Comprueba que existe `nombres_nadadores.csv` con columnas `epc` y `nombre`. Al ejecutar `cruzar_resultados.py` debe salir "Nombres cargados: N desde nombres_nadadores.csv". Si los EPC en resultados tienen prefijo `00` (26 caracteres), el cruce los normaliza a 24 caracteres; no hace falta cambiar archivos.

---

## Personalización

- **Registro** (`CompetenciaManager.registrar_llegada`): filtrar por antena, tiempo mínimo entre detecciones, validar EPCs conocidos.
- **Carriles por antena**: mapear número de antena a carril (ej. diccionario `CARRILES = {1: "Carril 1", 2: "Carril 2", ...}`).

---

## Archivos generados (resumen)

| Origen | Archivos |
|--------|----------|
| **rfid_nadadores** | `resultados_nadadores.csv` |
| **rfid_nadadores + planilla** | `resultados_con_nadadores.csv` (EPC, nombre si hay `nombres_nadadores.csv`, número, categoría, género, distancia, tiempos, epc_en_planilla) |
| **cruzar_resultados** | `resultados_con_nadadores.csv` (mismo; opcionalmente usa `nombres_nadadores.csv`) |
| **generar_epcs** | `tags_para_registro.csv`, `tags_completo.json`, `epcs_para_writer.txt`, `reporte_totales.pdf` (totales por categoría) |

---

## Otros programas del proyecto

- **Generador de EPCs** (`generar_epcs.py`): Define hasta 4 distancias, nadadores por distancia y F/M; genera EPCs y exporta **TXT**, **CSV** y **JSON**. Ver **README_EPC_GENERATION.md**.
- **Cruce de resultados** (`cruzar_resultados.py`): Cruce resultados de carrera con planilla de EPCs; se ejecuta solo o desde rfid_nadadores al guardar.

---

## Referencias

- SDK del equipo (Demo/lector del fabricante).
- Manual: documentación del fabricante del R300 YRM200.
