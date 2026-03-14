# 📘 Guía Completa - Generador de EPCs RFID

Generador de códigos EPC para competencias de natación (FECNA). **Tú defines** hasta 4 distancias (carreras), el **número de nadadores en cada una** y, por carrera, **femeninos y masculinos** (F+M debe sumar ese total). Exporta **TXT** (para el writer), **CSV** (planilla) y **JSON** (backup).

**Ejecución:** desde la raíz del proyecto: `python generar_epcs.py` o `python3 generar_epcs.py`.

## 🎯 Uso

### Modo interactivo

```bash
python generar_epcs.py
```

El programa pide:

- **Cuántas distancias (carreras) simultáneas** (1 a 4).
- Por cada carrera: **distancia** (1K/2K/3K/5K), **número de nadadores** en esa distancia, y luego **femeninos** y **masculinos** (F+M debe sumar ese total).
- El total de nadadores del evento es la suma de todas las distancias. Las categorías FECNA se reparten automáticamente.

**Ejemplo:**
```
¿Cuántas distancias (carreras) simultáneas? (1 a 4): 3
--- Carrera 1 ---
  Distancia (1K/2K/3K/5K): 1K
  Número de nadadores en 1K: 20
  De esos 20, número de FEMENINOS [10]: 10
  De esos 20, número de MASCULINOS [10]: 10
--- Carrera 2 ---
  Distancia (1K/2K/3K/5K): 2K
  Número de nadadores en 2K: 35
  De esos 35, número de FEMENINOS [17]: 17
  De esos 35, número de MASCULINOS [18]: 18
--- Carrera 3 ---
  ...
→ Total de nadadores: (suma de todas las distancias)
```

---

### Por código Python

Siempre usas **cantidad** por distancia (las cantidades deben sumar el total de nadadores):

```python
from generar_epcs import EPCGenerator

gen = EPCGenerator(prefijo_evento="2026")

# Cantidad por distancia debe sumar total_nadadores
config = gen.generar_distribucion_automatica(
    total_nadadores=100,
    distancias_config=[
        {
            'distancia': '2K',
            'cantidad': 35,
            'cantidad_femenino': 17,
            'cantidad_masculino': 18
        },
        {
            'distancia': '3K',
            'cantidad': 65,
            'cantidad_femenino': 32,
            'cantidad_masculino': 33
        }
    ]
)

gen.generar_lote_carreras(config)
# Exportar (nombres por defecto del proyecto)
gen.exportar_para_writer('epcs_para_writer.txt')
gen.exportar_csv('tags_para_registro.csv')
gen.exportar_json('tags_completo.json')
```

Si quieres otros nombres de archivo, pasa el path a cada `exportar_*`.

---

## 🔧 Parámetros Configurables

### 1. Total de Nadadores

```python
total_nadadores=100  # Ajustar a tu número de tags disponibles
```

### 2. Cantidad por distancia

Cada distancia lleva **cantidad** (número de nadadores). La suma de todas las cantidades debe ser igual a **total_nadadores**.

```python
{
    'distancia': '2K',
    'cantidad': 35  # 35 nadadores en 2K
}
# Si hay dos distancias, ej: 35 + 65 = 100
```

### 3. Cantidad por género (femenino / masculino)

Tú defines cuántos son femenino y cuántos masculino por distancia. Deben sumar el total de esa distancia.

```python
# Opción A: indicar ambos (deben sumar el total de la distancia)
'cantidad_femenino': 20,
'cantidad_masculino': 20   # 40 nadadores en esa distancia

# Opción B: solo femenino; masculino = total - cantidad_femenino
'cantidad_femenino': 25

# Opción C: solo masculino; femenino = total - cantidad_masculino
'cantidad_masculino': 35

# Si no indicas ninguno: se usa mitad y mitad por defecto
```

### 4. Categorías de Enfoque

```python
# Usar solo ciertas categorías
'categorias_enfoque': ['INF_A', 'INF_B', 'JUV_A']

# O usar todas (en generar_distribucion_automatica)
usar_todas_categorias=True
```

### 5. Distancias Disponibles

```python
'distancia': '1K'  # 1000 metros
'distancia': '2K'  # 2000 metros
'distancia': '3K'  # 3000 metros
'distancia': '5K'  # 5000 metros
```

### 6. Estructura del EPC (24 caracteres hex)

Cada EPC tiene **24 caracteres hexadecimales** (12 bytes):

| Parte      | Tamaño | Contenido |
|-----------|--------|-----------|
| Header    | 2      | E2 (fijo) |
| Evento    | 2      | 80 (fijo) |
| Año       | 4      | Ej. 07EA = 2026 |
| Distancia | 2      | 01=1K, 02=2K, 03=3K, 05=5K |
| Categoría | 2      | Código FECNA |
| Género    | 2      | 01=F, 02=M |
| Corredor  | 6      | Número 1–999 (3 bytes) |
| Reserved  | 2      | 00 |
| Checksum  | 2      | XOR de los bytes anteriores |

La **distancia** va codificada en el EPC, por eso puedes registrar varias carreras (distancias) con el mismo punto cero y separar resultados por la columna **distancia** en `resultados_con_nadadores.csv` (ver README.md). El **prefijo_evento** (parte Año/evento en el EPC) podría usarse en el futuro como identificador de evento si se amplía el sistema para varios eventos con distinto punto cero cada uno.

---

## 📊 Ejemplos Prácticos

### Ejemplo 1: 80 tags, 30 en 2K, 50 en 3K

**Interactivo:** `python generar_epcs.py` → Cuántas distancias: 2 → Carrera 1: 2K, 30 nadadores, F/M (ej. 15/15) → Carrera 2: 3K, 50 nadadores, F/M (ej. 25/25).

**Por código:**
```python
gen = EPCGenerator(prefijo_evento="2026")

config = gen.generar_distribucion_automatica(
    total_nadadores=80,
    distancias_config=[
        {'distancia': '2K', 'cantidad': 30, 'cantidad_femenino': 15, 'cantidad_masculino': 15},
        {'distancia': '3K', 'cantidad': 50, 'cantidad_femenino': 25, 'cantidad_masculino': 25}
    ]
)

gen.generar_lote_carreras(config)
```

### Ejemplo 2: 100 tags, 25 en 1K, 75 en 5K

```python
gen = EPCGenerator(prefijo_evento="2026")

config = gen.generar_distribucion_automatica(
    total_nadadores=100,
    distancias_config=[
        {'distancia': '1K', 'cantidad': 25, 'cantidad_femenino': 12, 'cantidad_masculino': 13},
        {'distancia': '5K', 'cantidad': 75, 'cantidad_femenino': 37, 'cantidad_masculino': 38}
    ]
)

gen.generar_lote_carreras(config)
```

### Ejemplo 3: 60 tags, solo mujeres mayores en 3K

```python
gen = EPCGenerator(prefijo_evento="2026")

config = gen.generar_distribucion_automatica(
    total_nadadores=60,
    distancias_config=[
        {
            'distancia': '3K',
            'cantidad': 60,
            'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B'],
            'cantidad_femenino': 60,
            'cantidad_masculino': 0
        }
    ],
    usar_todas_categorias=False
)

gen.generar_lote_carreras(config)
```

### Ejemplo 4: 120 tags, tres distancias con cantidades exactas

```python
gen = EPCGenerator(prefijo_evento="2026")

# Nota: Para 3+ distancias, usa código directo
config = [
    {
        'distancia': '1K',
        'categorias': [
            ('INF_A', 'F', 10),
            ('INF_A', 'M', 10),
        ]
    },
    {
        'distancia': '2K',
        'categorias': [
            ('JUV_A', 'F', 20),
            ('JUV_A', 'M', 20),
        ]
    },
    {
        'distancia': '3K',
        'categorias': [
            ('MAY_A', 'F', 30),
            ('MAY_A', 'M', 30),
        ]
    }
]

gen.generar_lote_carreras(config)
```

---

## 🎛️ Validaciones

El sistema exige **cantidad** en cada distancia y valida que la suma sea igual al total:
```python
# ✅ CORRECTO: Suma 100 (igual al total)
total_nadadores=100
[
    {'distancia': '2K', 'cantidad': 35},
    {'distancia': '3K', 'cantidad': 65}
]

# ❌ ERROR: Suma 110
total_nadadores=100
[
    {'distancia': '2K', 'cantidad': 50},
    {'distancia': '3K', 'cantidad': 60}
]
# Mensaje: "Las cantidades deben sumar 100, suman 110"
```

---

## 🔄 Workflow

### Opción A: Modo Interactivo

```bash
# 1. Ejecutar
python generar_epcs.py

# 2. Responder: cuántas distancias (1 a 4). Por cada carrera: distancia, nº de nadadores, luego nº femeninos y masculinos (F+M = total de esa carrera).
# 3. Al terminar se exportan:
#    - epcs_para_writer.txt (para writer RFID)
#    - tags_para_registro.csv (para Excel / cruzar_resultados)
#    - tags_completo.json (backup)
```

### Opción B: Script Personalizado

```python
# archivo: mis_tags.py
from generar_epcs import EPCGenerator

def generar_mis_tags():
    gen = EPCGenerator(prefijo_evento="2026")
    
    config = gen.generar_distribucion_automatica(
        total_nadadores=100,
        distancias_config=[
            {'distancia': '2K', 'cantidad': 35, 'cantidad_femenino': 17, 'cantidad_masculino': 18},
            {'distancia': '3K', 'cantidad': 65, 'cantidad_femenino': 32, 'cantidad_masculino': 33}
        ]
    )
    
    gen.generar_lote_carreras(config)
    gen.exportar_para_writer('mis_100_tags.txt')
    gen.exportar_csv('mis_100_tags.csv')
    gen.exportar_json('mis_100_tags.json')
    gen.imprimir_resumen()
    
    print(f"\n✅ Generados {len(gen.tags_generados)} tags")

if __name__ == "__main__":
    generar_mis_tags()
```

---

## 💡 Tips Avanzados

### 1. Ajustar cantidades según inscripciones

```python
# Más mujeres en 2K: 26 F, 14 M
{'distancia': '2K', 'cantidad': 40, 'cantidad_femenino': 26, 'cantidad_masculino': 14}

# Más hombres en 3K: 27 F, 33 M
{'distancia': '3K', 'cantidad': 60, 'cantidad_femenino': 27, 'cantidad_masculino': 33}
```

### 2. Enfocar categorías por edad

```python
# Solo niños en 2K
{
    'distancia': '2K',
    'cantidad': 30,
    'categorias_enfoque': ['INF_A', 'INF_B'],
    'cantidad_femenino': 15,
    'cantidad_masculino': 15
}

# Solo adultos en 3K
{
    'distancia': '3K',
    'cantidad': 70,
    'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B'],
    'cantidad_femenino': 35,
    'cantidad_masculino': 35
}
```

### 3. Modificar total sin cambiar proporciones

```python
# Original: 100 tags (35 + 65)
total_original = 100
dist1_original = 35
dist2_original = 65

# Nuevo total: 80 tags (mantener proporción)
total_nuevo = 80
dist1_nuevo = int(80 * 35 / 100)  # 28
dist2_nuevo = 80 - dist1_nuevo      # 52
```

---

## 🎯 Casos de Uso por Tamaño de Evento

### Evento Pequeño (30-50 nadadores)
```python
# Una sola carrera
total_nadadores=40
distancias_config=[
    {'distancia': '2K', 'cantidad': 40, 'cantidad_femenino': 20, 'cantidad_masculino': 20}
]
```

### Evento Mediano (50-100 nadadores)
```python
# Dos carreras
total_nadadores=80
distancias_config=[
    {'distancia': '2K', 'cantidad': 30, 'cantidad_femenino': 15, 'cantidad_masculino': 15},
    {'distancia': '3K', 'cantidad': 50, 'cantidad_femenino': 25, 'cantidad_masculino': 25}
]
```

### Evento Grande (100+ nadadores)
```python
# Mismo flujo: hasta 4 distancias, nadadores y F/M por cada una
# O usar código Python con generar_distribucion_automatica() para más control
```

---

## 📁 Archivos exportados (TXT, CSV, JSON)

Al finalizar, el programa genera **tres archivos** en formatos adecuados:

| Formato | Archivo | Contenido |
|--------|---------|-----------|
| **TXT** | `epcs_para_writer.txt` | Un EPC por línea, sin espacios; para copiar al writer RFID. |
| **CSV** | `tags_para_registro.csv` | Planilla: `epc_formateado`, `numero_corredor`, `categoria_nombre`, `genero`, `distancia`, `edad_min`, `edad_max`. Usado por `cruzar_resultados.py`. |
| **JSON** | `tags_completo.json` | Backup con metadata completa del evento y de cada tag. |

Para la **estructura exacta** del CSV y cómo editarlo a mano (p. ej. añadir columna `nombre`), ver en **README.md** la sección *Estructura de tags_para_registro.csv*.

El archivo **tags_para_registro.csv** también se usa en **`generar_planilla_inscripcion.py`**: con la opción `--nombres ... --tags tags_para_registro.csv` se generan los EPC para **nombres_nadadores.csv** leyendo la columna **epc_formateado** por orden de fila (fila 1 de inscripción = fila 1 de tags). Ver **README.md** → *generar_planilla_inscripcion.py*.

En modo interactivo los archivos se generan con esos nombres en el directorio actual. Al terminar se muestra la **verificación de género**: Femenino (X) + Masculino (Y) = Total ✓.

---

## ✅ Checklist Final

- [ ] Número de distancias (1 a 4) y, por cada una: distancia (1K/2K/3K/5K), nº de nadadores, femeninos y masculinos (F+M = total de esa carrera)
- [ ] EPCs generados y exportados (TXT, CSV, JSON)
- [ ] CSV abierto en Excel y verificado
- [ ] Tags listos para programar en writer RFID

---

Para el **registro de tiempos en carrera** (EPC + tiempo por nadador), usa **`rfid_nadadores.py`**; ver **README.md** del proyecto. El EPC codifica **distancia** (1K, 2K, 3K, 5K), así que puedes registrar varias distancias con el mismo punto cero y separar resultados filtrando por la columna **distancia** en `resultados_con_nadadores.csv`.
