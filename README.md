# Sistema de Control RFID para Nadadores

Software para el control y registro de tiempos en natación usando **RFID UHF** con el lector **R300 YRM200** (RFID reader module). Conexión por TCP/IP; el tiempo de cada nadador se calcula desde un **punto cero** que tú defines (inicio de carrera).

**Salidas:** Se usa **CSV** para resultados y planillas (Excel, cruce) y **JSON** para backup con metadata. El único **TXT** es la lista de EPCs para el writer (`epcs_para_writer.txt`), que muchos equipos esperan en ese formato.

**Resumen rápido:**
- **`test_conexion.py`**: Prueba de conexión al lector. Rotación de antenas (0,5 s), inventario 0x89+0x80/0x90. Muestra **"Tag leído: EPC=... Ant=X RSSI=X dBm"**.
- **`rfid_nadadores.py`**: Registra llegadas por EPC, ignora 000000, asigna antena correcta. Exporta **`resultados_nadadores.csv`**; si hay planilla, genera **`resultados_con_nadadores.csv`**.
- **`cruzar_resultados.py`**: Cruza resultados con planilla y opcionalmente **`nombres_nadadores.csv`** (epc, nombre, categoria, sexo). Rellena nombre, categoría y género desde ese archivo o desde la planilla. Genera **`resultados_con_nadadores.csv`** (con tiempo en formato hh:mm:ss.ccc) y llama a **`clasificacion.py`**.
- **`clasificacion.py`**: A partir de `resultados_con_nadadores.csv` genera **`clasificacion.csv`**, **`clasificacion.xlsx`** y **`clasificacion.pdf`** (posición general y por categoría+sexo simultáneo; tiempo en hh:mm:ss.ccc; requiere fpdf2 y openpyxl).
- **`generar_planilla_inscripcion.py`**: Genera planilla de inscripción en Excel (nombre, categoria, genero, club, tiempo_inscripcion) y puede generar **`nombres_nadadores.csv`** leyendo los EPC desde **`tags_para_registro.csv`** por orden de fila.
- **`generar_epcs.py`**: Generador de EPCs por categoría y género. Exporta CSV, JSON, TXT y PDF. Ver **README_EPC_GENERATION.md**.

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

### `cruzar_resultados.py` – Cruce EPC → nadador (nombre, categoría, género)

Cruza los resultados de la carrera con la planilla de EPCs y genera **`resultados_con_nadadores.csv`** con: posición, EPC, **nombre**, número corredor, **categoría**, **género**, distancia, hora llegada, **tiempo_carrera_s** y **tiempo_carrera** (formato hh:mm:ss.ccc), antena, rssi, edades y **`epc_en_planilla`** (sí/no).

- **Planilla**: `tags_para_registro.csv` (generada por `generar_epcs.py` o editada a mano). Obligatoria para el cruce. Ver más abajo **Estructura de `tags_para_registro.csv`**.
- **Nombres / categoría / género**: Si existe **`nombres_nadadores.csv`** con columnas **`epc`**, **`nombre`**, **`categoria`** y **`sexo`**, se usan para el cruce por EPC. La columna **nombre**, **categoria_nombre** y **genero** del CSV de salida se rellenan desde ese archivo (si no, desde la planilla). Acepta cabeceras con BOM y variantes (categoria_nombre, genero). Los CSV pueden estar en **UTF-8, cp1252 o latin-1**.
- **Normalización de EPC**: Se quitan espacios; si el EPC tiene más de 24 caracteres hex (ej. prefijo `00` en resultados del lector), se usan los últimos 24 para el cruce.
- **Integrado**: Al guardar resultados, `rfid_nadadores.py` ejecuta el cruce si existe `tags_para_registro.csv`.
- **Manual**: `python cruzar_resultados.py`.

**Formato `nombres_nadadores.csv`:**
```csv
epc,nombre,categoria,sexo
E2 80 07 EA 02 01 01 00 00 01 00 8C,Clara Méndez,Juvenil A,Femenino
E28007EA020502000001008B,Camila Herrera,Infantil B,Femenino
```
EPC puede ir con o sin espacios; se normaliza al cruzar. Las columnas **categoria** y **sexo** se usan para la clasificación por categoría y género.

**Estructura de `tags_para_registro.csv`** (para cruce y planilla):

Este archivo lo genera **`generar_epcs.py`** al exportar a CSV. Si lo editas a mano, debe tener **exactamente** estas columnas (el orden puede variar si usas DictReader con fieldnames; aquí el orden que usa generar_epcs):

| Columna            | Descripción                                                                 | Ejemplo                    |
|--------------------|-----------------------------------------------------------------------------|----------------------------|
| `epc_formateado`   | EPC en hex con espacios (24 caracteres hex = 12 bytes). **Clave para el cruce.** | `E2 80 07 EA 02 01 01 00 00 01 00 8C` |
| `numero_corredor`  | Número del corredor (entero)                                                | `1`                        |
| `categoria_nombre` | Nombre de la categoría FECNA                                                | `Infantil A`, `Juvenil B`  |
| `genero`           | Femenino o Masculino                                                        | `Femenino`                 |
| `distancia`        | Distancia en metros (código o valor)                                        | `2000`, `2K`               |
| `edad_min`         | Edad mínima de la categoría                                                 | `8`                        |
| `edad_max`         | Edad máxima de la categoría                                                 | `9`                        |

**Opcional** (si editas a mano y quieres que el nombre salga en el cruce sin usar `nombres_nadadores.csv`): puedes añadir la columna **`nombre`** o **`nombre_nadador`**; `cruzar_resultados.py` la usará para rellenar la columna nombre en `resultados_con_nadadores.csv`.

- **generar_epcs** escribe solo las 7 columnas anteriores (sin nombre).
- **cruzar_resultados** lee la planilla por **`epc_formateado`** (normalizado: sin espacios, mayúsculas; si hay más de 24 hex usa los últimos 24) y usa las columnas `numero_corredor`, `categoria_nombre`, `genero`, `distancia`, `edad_min`, `edad_max` para rellenar el CSV de salida. Si existe la columna `nombre` o `nombre_nadador` en la planilla, también la usa.

**Clasificación por tiempo:** Tras el cruce, se ejecuta automáticamente **`clasificacion.py`**, que genera:
- **`clasificacion.csv`** y **`clasificacion.xlsx`**: **posicion_general**, **posicion_categoria_sexo** (clasificación simultánea por categoría y sexo), nombre, categoría, género, **tiempo_carrera** (hh:mm:ss.ccc), etc.
- **`clasificacion.pdf`**: tablas en PDF con clasificación general y por categoría+sexo (requiere `fpdf2`; si falla, se muestra el error y se sugiere `pip install fpdf2`).

También puedes ejecutar la clasificación a mano: `python clasificacion.py` (lee `resultados_con_nadadores.csv`). Para usar otro CSV: `python clasificacion.py mi_resultados.csv`.

---

### `generar_planilla_inscripcion.py` – Planilla de inscripción y generación de nombres_nadadores

Genera una **planilla de inscripción en Excel** (columnas: nombre, categoria, genero, club, tiempo_inscripcion) para rellenar datos de nadadores y, a partir de ella, **generar `nombres_nadadores.csv`** con los EPC leídos desde **`tags_para_registro.csv`** (asignación por orden de fila: fila 1 inscripción = fila 1 tags).

**Uso:**
```bash
# Crear planilla Excel (100 filas por defecto)
python generar_planilla_inscripcion.py
python generar_planilla_inscripcion.py mi_planilla.xlsx -n 150

# Exportar la planilla a CSV (solo columnas de la hoja)
python generar_planilla_inscripcion.py --export planilla_inscripcion.xlsx inscripcion.csv

# Generar nombres_nadadores.csv desde la planilla, leyendo EPCs de tags_para_registro
python generar_planilla_inscripcion.py --nombres planilla_inscripcion.xlsx nombres_nadadores.csv --tags tags_para_registro.csv
```

**Importante:** El orden de las filas en la planilla de inscripción debe coincidir con el de `tags_para_registro.csv` (misma persona en la misma línea). Los EPC se toman siempre de la columna **epc_formateado** de `tags_para_registro.csv`.

---

### `clasificacion.py` – Clasificación por tiempo (general, categoría+sexo)

Genera la **clasificación ordenada por tiempo de carrera** a partir de `resultados_con_nadadores.csv` (se ejecuta automáticamente al final de `cruzar_resultados.py`).

**Salidas:**
- **`clasificacion.csv`** y **`clasificacion.xlsx`**: Una fila por participante con **posicion_general**, **posicion_categoria_sexo** (posición dentro del grupo categoría+sexo, p. ej. Juvenil Femenino), nombre, categoría, género, **tiempo_carrera** en formato **hh:mm:ss.ccc**, etc. Requiere **openpyxl** para Excel.
- **`clasificacion.pdf`**: PDF con (1) Clasificación general y (2) Por categoría y sexo (una tabla por cada combinación, p. ej. "Juvenil — Femenino"). Requiere **fpdf2** (`pip install fpdf2`). Si falla la generación del PDF, se muestra el error en pantalla.

**Uso:**
```bash
python clasificacion.py
# Con otro CSV de entrada:
python clasificacion.py mi_resultados.csv
```

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

- **Python 3** (3.6+). Casi todo el proyecto usa solo la biblioteca estándar.
- **fpdf2** (PDF) y **openpyxl** (Excel): `pip install -r requirements.txt`.
- PC en la misma red que el lector.

```bash
python --version  # Verificar 3.6+
python -m venv venv   # Opcional: entorno virtual
# En Windows: venv\Scripts\activate   En Linux/Mac: source venv/bin/activate
pip install -r requirements.txt  # fpdf2 (PDF), openpyxl (Excel)
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
6. **Ctrl+C** para finalizar; se guarda `resultados_nadadores.csv`. Si existe `tags_para_registro.csv`, se genera **`resultados_con_nadadores.csv`** (con nombre si existe `nombres_nadadores.csv`).
7. Para cruce y clasificación por tiempo: ejecuta **`python cruzar_resultados.py`**. Se generan **`resultados_con_nadadores.csv`** (con tiempo en hh:mm:ss.ccc), **`clasificacion.csv`**, **`clasificacion.xlsx`** y **`clasificacion.pdf`** (clasificación general y por categoría+sexo).
8. Opcional – planilla de inscripción: **`python generar_planilla_inscripcion.py`** crea la planilla Excel; tras rellenarla, **`python generar_planilla_inscripcion.py --nombres planilla_inscripcion.xlsx nombres_nadadores.csv --tags tags_para_registro.csv`** genera **`nombres_nadadores.csv`** con EPCs leídos de la planilla de tags.

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

**Archivo `resultados_con_nadadores.csv`** (si existe planilla `tags_para_registro.csv`; nombre, categoría y género desde `nombres_nadadores.csv` o planilla; **tiempo_carrera** en hh:mm:ss.ccc; **epc_en_planilla**: sí/no):
```csv
inicio_punto_cero,2025-02-22 14:23:12.667
posicion,epc,nombre,numero_corredor,categoria_nombre,genero,distancia,hora_llegada,tiempo_carrera_s,tiempo_carrera,antena,rssi,edad_min,edad_max,epc_en_planilla
1,E2801190...,María García,1,Infantil A,Femenino,2000,14:23:45.123,32.456,00:00:32.456,1,-50,8,9,sí
2,E2801191...,Carlos López,2,Juvenil A,Masculino,2000,14:23:46.789,34.122,00:00:34.122,2,-48,12,13,sí
```
Con este archivo sabes **qué nadador es** cada EPC (nombre, número, categoría, género, distancia). Si en una misma salida compites **varias distancias** (p. ej. 2K y 3K) con el **mismo punto cero**, todas las llegadas quedan en este CSV; puedes separar por carrera **filtrando por la columna `distancia`** en Excel.

El **tiempo de carrera** de cada nadador es el número de segundos desde el punto cero hasta la detección de su tag.

**Archivos de clasificación** (tras `cruzar_resultados.py` o `python clasificacion.py`):
- **clasificacion.csv** / **clasificacion.xlsx**: Una fila por participante con **posicion_general**, **posicion_categoria_sexo**, nombre, categoría, género, **tiempo_carrera** (hh:mm:ss.ccc), etc. Orden por posición general.
- **clasificacion.pdf**: Tablas listas para imprimir: clasificación general y por categoría+sexo (requiere `fpdf2`).

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

**Nombres / categoría / género no aparecen en resultados_con_nadadores.csv**
- Comprueba que existe `nombres_nadadores.csv` con columnas **epc**, **nombre**, **categoria** y **sexo**. Al ejecutar `cruzar_resultados.py` debe salir "Datos de cruce cargados: N filas desde nombres_nadadores.csv". Puedes generar ese CSV desde la planilla de inscripción con `generar_planilla_inscripcion.py --nombres ... --tags tags_para_registro.csv` (los EPC se leen de `tags_para_registro` por orden de fila).

**No se genera clasificacion.pdf**
- Instala **fpdf2**: `pip install fpdf2`. Si falla, el script muestra el error (p. ej. caracteres no soportados por la fuente; el PDF usa texto compatible con Helvetica).

---

## Personalización

- **Registro** (`CompetenciaManager.registrar_llegada`): filtrar por antena, tiempo mínimo entre detecciones, validar EPCs conocidos.
- **Carriles por antena**: mapear número de antena a carril (ej. diccionario `CARRILES = {1: "Carril 1", 2: "Carril 2", ...}`).

---

## Archivos generados (resumen)

| Origen | Archivos |
|--------|----------|
| **rfid_nadadores** | `resultados_nadadores.csv` |
| **rfid_nadadores + planilla** | `resultados_con_nadadores.csv` (EPC, nombre, categoría, género, tiempos en hh:mm:ss.ccc, epc_en_planilla) |
| **cruzar_resultados** | `resultados_con_nadadores.csv` (y llama a clasificacion) |
| **clasificacion** | `clasificacion.csv`, `clasificacion.xlsx`, `clasificacion.pdf` (clasificación general y categoría+sexo; tiempo en hh:mm:ss.ccc) |
| **generar_planilla_inscripcion** | `planilla_inscripcion.xlsx` (nombre, categoria, genero, club, tiempo_inscripcion); con `--nombres --tags` genera **`nombres_nadadores.csv`** (EPCs desde tags_para_registro) |
| **generar_epcs** | `tags_para_registro.csv`, `tags_completo.json`, `epcs_para_writer.txt`, `reporte_totales.pdf` (totales por categoría) |

---

## Otros programas del proyecto

- **Generador de EPCs** (`generar_epcs.py`): Define distancias y nadadores por categoría/género; exporta CSV, JSON, TXT y PDF. Ver **README_EPC_GENERATION.md**.
- **Planilla de inscripción** (`generar_planilla_inscripcion.py`): Genera Excel de inscripción (nombre, categoria, genero, club, tiempo_inscripcion) y, con `--nombres --tags`, genera **nombres_nadadores.csv** leyendo EPCs desde **tags_para_registro.csv** por orden de fila.
- **Cruce de resultados** (`cruzar_resultados.py`): Cruce con planilla y opcionalmente nombres_nadadores.csv (epc, nombre, categoria, sexo); genera `resultados_con_nadadores.csv` (tiempo en hh:mm:ss.ccc) y dispara la clasificación.
- **Clasificación** (`clasificacion.py`): Clasificación por tiempo (general y categoría+sexo simultáneo); genera CSV, Excel y PDF con tiempo en hh:mm:ss.ccc. Se ejecuta tras el cruce o a mano.

---

## Referencias

- SDK del equipo (Demo/lector del fabricante).
- Manual: documentación del fabricante del R300 YRM200.
