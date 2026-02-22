#!/usr/bin/env python3
"""
Generador de códigos EPC para tags RFID - Competencias de Natación
Sistema basado en categorías FECNA (Federación Colombiana de Natación)
"""
import json
from typing import List, Dict
from datetime import datetime


class EPCGenerator:
    """Genera códigos EPC estructurados para competencias de natación"""
    
    # Categorías FECNA por grupos de edad
    CATEGORIAS_FECNA = {
        # Código: (nombre, edad_min, edad_max)
        'INF_A': ('Infantil A', 8, 9),
        'INF_B': ('Infantil B', 10, 11),
        'JUV_A': ('Juvenil A', 12, 13),
        'JUV_B': ('Juvenil B', 14, 15),
        'JUN_A': ('Junior A', 16, 17),
        'JUN_B': ('Junior B', 18, 19),
        'MAY_A': ('Mayores A', 20, 24),
        'MAY_B': ('Mayores B', 25, 29),
        'MAS_A': ('Masters A', 30, 39),
        'MAS_B': ('Masters B', 40, 49),
        'MAS_C': ('Masters C', 50, 59),
        'MAS_D': ('Masters D', 60, 99),
    }
    
    # Códigos de género
    GENERO = {
        'F': 'Femenino',
        'M': 'Masculino'
    }
    
    # Distancias comunes (en metros)
    DISTANCIAS = {
        '2K': 2000,
        '3K': 3000,
        '5K': 5000,
        '1K': 1000,
    }
    
    def __init__(self, prefijo_evento: str = "2026"):
        """
        Inicializar generador
        prefijo_evento: Identificador del evento (ej: año, código de carrera)
        """
        self.prefijo_evento = prefijo_evento
        self.tags_generados = []
    
    @staticmethod
    def calcular_checksum(epc_sin_check: str) -> str:
        """
        Calcula checksum simple para EPC (XOR de todos los bytes)
        epc_sin_check: String hex sin espacios (22 caracteres = 11 bytes)
        Retorna: 2 caracteres hex (1 byte de checksum)
        """
        if len(epc_sin_check) != 22:
            raise ValueError(f"EPC debe tener 22 caracteres hex, tiene {len(epc_sin_check)}")
        
        checksum = 0
        # Procesar de 2 en 2 (cada byte)
        for i in range(0, len(epc_sin_check), 2):
            byte_val = int(epc_sin_check[i:i+2], 16)
            checksum ^= byte_val  # XOR
        
        return f"{checksum:02X}"
    
    @staticmethod
    def formato_epc_legible(epc: str) -> str:
        """Formatea EPC con espacios para legibilidad"""
        # Dividir en grupos de 2 caracteres
        return ' '.join(epc[i:i+2] for i in range(0, len(epc), 2))
    
    def generar_epc(self, categoria: str, genero: str, distancia: str, 
                    numero_corredor: int) -> Dict:
        """
        Genera un código EPC estructurado de 24 caracteres hex (12 bytes)
        
        Estructura:
        [Header:2][Evento:2][Año:4][Distancia:2][Categoría:2][Género:2][Corredor:6][Reserved:2][Checksum:2]
        Total: 22 chars (11 bytes) + 2 checksum = 24 chars (12 bytes)
        
        Retorna dict con EPC completo y metadata
        """
        # Validaciones
        if categoria not in self.CATEGORIAS_FECNA:
            raise ValueError(f"Categoría inválida: {categoria}")
        if genero not in self.GENERO:
            raise ValueError(f"Género inválido: {genero}")
        if distancia not in self.DISTANCIAS:
            raise ValueError(f"Distancia inválida: {distancia}")
        if not 1 <= numero_corredor <= 999:
            raise ValueError(f"Número de corredor debe estar entre 1-999")
        
        # 1. Header EPC estándar (2 chars = 1 byte)
        header_hex = 'E2'
        
        # 2. Identificador de evento (2 chars = 1 byte)
        evento_hex = '80'  # Identificador fijo
        
        # 3. Año (4 chars = 2 bytes)
        if self.prefijo_evento.isdigit() and len(self.prefijo_evento) >= 4:
            anio_val = int(self.prefijo_evento[:4])
            anio_hex = f'{anio_val:04X}'
        else:
            anio_hex = '07EA'  # 2026 en hex
        
        # 4. Distancia (2 chars = 1 byte)
        dist_map = {'1K': '01', '2K': '02', '3K': '03', '5K': '05'}
        dist_hex = dist_map.get(distancia, '00')
        
        # 5. Categoría (2 chars = 1 byte)
        cat_codes = {cat: f'{i:02X}' for i, cat in enumerate(self.CATEGORIAS_FECNA.keys(), 1)}
        cat_hex = cat_codes.get(categoria, '00')
        
        # 6. Género (2 chars = 1 byte)
        gen_hex = '01' if genero == 'F' else '02'
        
        # 7. Número de corredor (6 chars = 3 bytes)
        corredor_hex = f'{numero_corredor:06X}'
        
        # 8. Reserved/padding (2 chars = 1 byte)
        reserved_hex = '00'
        
        # Ensamblar EPC sin checksum (22 chars = 11 bytes)
        epc_sin_check = (header_hex + evento_hex + anio_hex + dist_hex + 
                        cat_hex + gen_hex + corredor_hex + reserved_hex)
        
        # Verificar longitud
        if len(epc_sin_check) != 22:
            raise ValueError(f"Error interno: EPC tiene {len(epc_sin_check)} chars, esperados 22")
        
        # 9. Calcular checksum (2 chars = 1 byte)
        checksum = self.calcular_checksum(epc_sin_check)
        
        # EPC completo (24 chars = 12 bytes)
        epc_completo = epc_sin_check + checksum
        
        # Crear registro completo
        tag_info = {
            'epc': epc_completo,
            'epc_formateado': self.formato_epc_legible(epc_completo),
            'numero_corredor': numero_corredor,
            'categoria_codigo': categoria,
            'categoria_nombre': self.CATEGORIAS_FECNA[categoria][0],
            'edad_min': self.CATEGORIAS_FECNA[categoria][1],
            'edad_max': self.CATEGORIAS_FECNA[categoria][2],
            'genero': self.GENERO[genero],
            'genero_codigo': genero,
            'distancia': self.DISTANCIAS[distancia],
            'distancia_codigo': distancia,
            'prefijo_evento': self.prefijo_evento,
            'checksum': checksum
        }
        
        self.tags_generados.append(tag_info)
        return tag_info
    
    def generar_lote_carreras(self, config_carreras: List[Dict]) -> List[Dict]:
        """
        Genera lote de EPCs para múltiples carreras
        
        config_carreras: Lista de configs, cada una con:
            - distancia: '2K', '3K', etc
            - categorias: lista de tuplas (categoria, genero, cantidad)
        
        Ejemplo:
        [
            {
                'distancia': '2K',
                'categorias': [
                    ('INF_A', 'F', 5),  # 5 corredoras Infantil A
                    ('INF_A', 'M', 5),  # 5 corredores Infantil A
                ]
            },
            {
                'distancia': '3K',
                'categorias': [...]
            }
        ]
        """
        tags_generados = []
        
        for carrera in config_carreras:
            distancia = carrera['distancia']
            
            for categoria, genero, cantidad in carrera['categorias']:
                # Generar tags para esta categoría/género
                for i in range(1, cantidad + 1):
                    tag = self.generar_epc(
                        categoria=categoria,
                        genero=genero,
                        distancia=distancia,
                        numero_corredor=i
                    )
                    tags_generados.append(tag)
        
        return tags_generados
    
    def generar_distribucion_automatica(self, 
                                       total_nadadores: int,
                                       distancias_config: List[Dict],
                                       usar_todas_categorias: bool = True) -> List[Dict]:
        """
        Genera distribución automática de tags según total de nadadores
        
        Args:
            total_nadadores: Número total de tags a generar (ej: 100)
            distancias_config: Lista de distancias con 'cantidad' cada una (las cantidades deben sumar total_nadadores).
                Ejemplo:
                [
                    {'distancia': '2K', 'cantidad': 40, 'cantidad_femenino': 20, 'cantidad_masculino': 20, ...},
                    {'distancia': '3K', 'cantidad': 60, 'cantidad_femenino': 30, 'cantidad_masculino': 30, ...}
                ]
                Opcional: cantidad_femenino/cantidad_masculino (si no, 50% F / 50% M). categorias_enfoque para restringir categorías.
            usar_todas_categorias: Si True, distribuye entre todas las categorías FECNA
        
        Returns:
            Lista de configuraciones listas para generar_lote_carreras()
        """
        if not distancias_config:
            raise ValueError("Debe proporcionar al menos una distancia en distancias_config")
        if 'cantidad' not in distancias_config[0]:
            raise ValueError("Cada distancia debe tener 'cantidad' (ej: {'distancia': '2K', 'cantidad': 40, ...})")

        total_cantidad = sum(d['cantidad'] for d in distancias_config)
        if total_cantidad != total_nadadores:
            raise ValueError(f"Las cantidades deben sumar {total_nadadores}, suman {total_cantidad}")

        config_carreras = []

        for dist_config in distancias_config:
            distancia = dist_config['distancia']
            nadadores_distancia = dist_config['cantidad']

            # Determinar categorías a usar
            if usar_todas_categorias:
                categorias_usar = list(self.CATEGORIAS_FECNA.keys())
            else:
                categorias_usar = dist_config.get('categorias_enfoque',
                                                  list(self.CATEGORIAS_FECNA.keys()))

            # Nadadores por género: tú defines cantidad_femenino y/o cantidad_masculino
            cant_f = dist_config.get('cantidad_femenino')
            cant_m = dist_config.get('cantidad_masculino')
            if cant_f is not None and cant_m is not None:
                if cant_f + cant_m != nadadores_distancia:
                    raise ValueError(
                        f"Distancia {distancia}: cantidad_femenino ({cant_f}) + cantidad_masculino ({cant_m}) "
                        f"debe sumar {nadadores_distancia}"
                    )
                nadadores_femenino = cant_f
                nadadores_masculino = cant_m
            elif cant_f is not None:
                nadadores_femenino = cant_f
                nadadores_masculino = nadadores_distancia - cant_f
                if nadadores_masculino < 0:
                    raise ValueError(
                        f"Distancia {distancia}: cantidad_femenino ({cant_f}) no puede ser mayor que {nadadores_distancia}"
                    )
            elif cant_m is not None:
                nadadores_masculino = cant_m
                nadadores_femenino = nadadores_distancia - cant_m
                if nadadores_femenino < 0:
                    raise ValueError(
                        f"Distancia {distancia}: cantidad_masculino ({cant_m}) no puede ser mayor que {nadadores_distancia}"
                    )
            else:
                # Por defecto: mitad y mitad
                nadadores_femenino = nadadores_distancia // 2
                nadadores_masculino = nadadores_distancia - nadadores_femenino
            
            # Distribuir entre categorías
            cats_por_genero = {
                'F': self._distribuir_en_categorias(nadadores_femenino, categorias_usar),
                'M': self._distribuir_en_categorias(nadadores_masculino, categorias_usar)
            }
            
            # Crear configuración de carrera
            categorias_lista = []
            for genero in ['F', 'M']:
                for categoria, cantidad in cats_por_genero[genero].items():
                    if cantidad > 0:
                        categorias_lista.append((categoria, genero, cantidad))
            
            config_carreras.append({
                'distancia': distancia,
                'categorias': categorias_lista
            })
        
        return config_carreras
    
    def _distribuir_en_categorias(self, total: int, categorias: List[str]) -> Dict[str, int]:
        """
        Distribuye nadadores equitativamente entre categorías
        Retorna dict {categoria: cantidad}
        """
        if total == 0 or not categorias:
            return {cat: 0 for cat in categorias}
        
        # Distribución base
        por_categoria = total // len(categorias)
        resto = total % len(categorias)
        
        distribucion = {}
        for i, cat in enumerate(categorias):
            distribucion[cat] = por_categoria
            # Distribuir el resto en las primeras categorías
            if i < resto:
                distribucion[cat] += 1
        
        return distribucion
    
    def exportar_csv(self, filename: str = 'tags_rfid.csv'):
        """Exporta tags a CSV para fácil impresión"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if not self.tags_generados:
                print("⚠ No hay tags para exportar")
                return
            
            campos = ['epc_formateado', 'numero_corredor', 'categoria_nombre', 
                     'genero', 'distancia', 'edad_min', 'edad_max']
            
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            
            for tag in self.tags_generados:
                writer.writerow({k: tag[k] for k in campos})
        
        print(f"✓ CSV exportado: {filename}")
    
    def exportar_json(self, filename: str = 'tags_rfid.json'):
        """Exporta tags a JSON con metadata completa"""
        data = {
            'evento': self.prefijo_evento,
            'fecha_generacion': datetime.now().isoformat(),
            'total_tags': len(self.tags_generados),
            'tags': self.tags_generados
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ JSON exportado: {filename}")
    
    def exportar_para_writer(self, filename: str = 'epcs_para_writer.txt'):
        """
        Exporta solo los códigos EPC en formato simple para copiar al writer
        Un EPC por línea, sin espacios
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for tag in self.tags_generados:
                f.write(f"{tag['epc']}\n")
        
        print(f"✓ EPCs para writer: {filename}")
    
    def imprimir_resumen(self):
        """Imprime resumen de tags generados"""
        print("\n" + "="*70)
        print(f"RESUMEN - Total Tags: {len(self.tags_generados)}")
        print("="*70)
        
        # Agrupar por distancia
        por_distancia = {}
        for tag in self.tags_generados:
            dist = tag['distancia_codigo']
            if dist not in por_distancia:
                por_distancia[dist] = []
            por_distancia[dist].append(tag)
        
        for dist, tags in por_distancia.items():
            print(f"\n📏 Distancia: {self.DISTANCIAS[dist]}m ({dist})")
            
            # Agrupar por categoría y género
            por_categoria = {}
            for tag in tags:
                key = (tag['categoria_codigo'], tag['genero_codigo'])
                if key not in por_categoria:
                    por_categoria[key] = []
                por_categoria[key].append(tag)
            
            for (cat, gen), tags_grupo in sorted(por_categoria.items()):
                cat_nombre = self.CATEGORIAS_FECNA[cat][0]
                gen_nombre = self.GENERO[gen]
                print(f"  • {cat_nombre} {gen_nombre}: {len(tags_grupo)} tags")
        
        print("\n" + "="*70)
    
    def imprimir_muestra(self, cantidad: int = 5):
        """Imprime muestra de los primeros tags generados"""
        print("\n" + "="*70)
        print(f"MUESTRA DE TAGS (primeros {cantidad})")
        print("="*70)
        
        for i, tag in enumerate(self.tags_generados[:cantidad], 1):
            print(f"\n{i}. EPC: {tag['epc_formateado']}")
            print(f"   Corredor #{tag['numero_corredor']}")
            print(f"   Categoría: {tag['categoria_nombre']} {tag['genero']}")
            print(f"   Distancia: {tag['distancia']}m")
            print(f"   Edades: {tag['edad_min']}-{tag['edad_max']} años")


# =============================================================================
# CONFIGURACIÓN DE EVENTO - MODIFICA AQUÍ TUS PARÁMETROS
# =============================================================================

def configurar_evento_ejemplo():
    """
    Configura un evento de ejemplo con 2 carreras
    MODIFICA ESTA FUNCIÓN según tus necesidades
    """
    
    # Crear generador con prefijo del evento
    generador = EPCGenerator(prefijo_evento="2026")
    
    # =================================================================
    # CARRERA 1: 2 KM
    # =================================================================
    carrera_2km = {
        'distancia': '2K',
        'categorias': [
            # (categoria_codigo, genero, cantidad_tags)
            
            # Infantiles (8-11 años)
            ('INF_A', 'F', 3),  # Infantil A Femenino (8-9)
            ('INF_A', 'M', 3),  # Infantil A Masculino (8-9)
            ('INF_B', 'F', 3),  # Infantil B Femenino (10-11)
            ('INF_B', 'M', 3),  # Infantil B Masculino (10-11)
            
            # Juveniles (12-15 años)
            ('JUV_A', 'F', 4),  # Juvenil A Femenino (12-13)
            ('JUV_A', 'M', 4),  # Juvenil A Masculino (12-13)
            ('JUV_B', 'F', 4),  # Juvenil B Femenino (14-15)
            ('JUV_B', 'M', 4),  # Juvenil B Masculino (14-15)
            
            # Juniors (16-19 años)
            ('JUN_A', 'F', 3),  # Junior A Femenino (16-17)
            ('JUN_A', 'M', 3),  # Junior A Masculino (16-17)
        ]
    }
    
    # =================================================================
    # CARRERA 2: 3 KM
    # =================================================================
    carrera_3km = {
        'distancia': '3K',
        'categorias': [
            # Mayores (20-29 años)
            ('MAY_A', 'F', 5),  # Mayores A Femenino (20-24)
            ('MAY_A', 'M', 5),  # Mayores A Masculino (20-24)
            ('MAY_B', 'F', 4),  # Mayores B Femenino (25-29)
            ('MAY_B', 'M', 4),  # Mayores B Masculino (25-29)
            
            # Masters (30+ años)
            ('MAS_A', 'F', 4),  # Masters A Femenino (30-39)
            ('MAS_A', 'M', 4),  # Masters A Masculino (30-39)
            ('MAS_B', 'F', 3),  # Masters B Femenino (40-49)
            ('MAS_B', 'M', 3),  # Masters B Masculino (40-49)
        ]
    }
    
    # =================================================================
    # Generar todos los tags
    # =================================================================
    config_completa = [carrera_2km, carrera_3km]
    generador.generar_lote_carreras(config_completa)
    
    return generador


# =============================================================================
# EJEMPLO DE USO PERSONALIZADO
# =============================================================================

def ejemplo_personalizado():
    """
    Ejemplo de cómo crear tu propia configuración
    Copia y modifica esta función según tus necesidades
    """
    
    # 1. Crear generador
    gen = EPCGenerator(prefijo_evento="2026")
    
    # 2. Definir tus carreras
    mis_carreras = [
        {
            'distancia': '2K',  # Opciones: '1K', '2K', '3K', '5K'
            'categorias': [
                # Formato: (categoria, genero, cantidad)
                ('INF_A', 'F', 5),  # 5 niñas 8-9 años
                ('INF_A', 'M', 5),  # 5 niños 8-9 años
                # Agrega más categorías aquí...
            ]
        },
        {
            'distancia': '3K',
            'categorias': [
                ('MAY_A', 'F', 10),
                ('MAY_A', 'M', 10),
                # Agrega más categorías aquí...
            ]
        }
    ]
    
    # 3. Generar tags
    gen.generar_lote_carreras(mis_carreras)
    
    # 4. Exportar
    gen.exportar_para_writer('mis_epcs.txt')
    gen.exportar_csv('mis_tags.csv')
    gen.exportar_json('mis_tags.json')
    gen.imprimir_resumen()
    
    return gen


def ejemplo_distribucion_automatica():
    """
    Ejemplo usando distribución automática según total de nadadores
    RECOMENDADO: Usa esta función cuando tengas un número fijo de tags
    """
    
    # 1. Crear generador
    gen = EPCGenerator(prefijo_evento="2026")
    
    # 2. Configurar distribución automática
    TOTAL_NADADORES = 100  # ← MODIFICAR: Total de tags disponibles
    
    distancias_config = [
        {
            'distancia': '2K',
            'cantidad': 40,
            'categorias_enfoque': ['INF_A', 'INF_B', 'JUV_A', 'JUV_B'],
            'cantidad_femenino': 20,
            'cantidad_masculino': 20
        },
        {
            'distancia': '3K',
            'cantidad': 60,
            'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B'],
            'cantidad_femenino': 33,
            'cantidad_masculino': 27
        }
    ]
    
    # 3. Generar configuración automática
    config = gen.generar_distribucion_automatica(
        total_nadadores=TOTAL_NADADORES,
        distancias_config=distancias_config,
        usar_todas_categorias=False  # Usa solo categorias_enfoque
    )
    
    # 4. Generar tags
    gen.generar_lote_carreras(config)
    
    # 5. Exportar
    gen.exportar_para_writer('epcs_auto.txt')
    gen.exportar_csv('tags_auto.csv')
    gen.exportar_json('tags_auto.json')
    gen.imprimir_resumen()
    
    print(f"\n💡 Se generaron exactamente {len(gen.tags_generados)} tags")
    print(f"   (solicitados: {TOTAL_NADADORES})")
    
    return gen


def ejemplo_cantidades_exactas():
    """
    Ejemplo especificando CANTIDADES EXACTAS por distancia (no porcentajes)
    Útil cuando sabes exactamente cuántos nadadores habrá en cada carrera
    """
    
    # 1. Crear generador
    gen = EPCGenerator(prefijo_evento="2026")
    
    # 2. Especificar cantidades EXACTAS (deben sumar el total)
    TOTAL_NADADORES = 100
    
    distancias_config = [
        {
            'distancia': '2K',
            'cantidad': 35,
            'categorias_enfoque': ['INF_A', 'INF_B', 'JUV_A', 'JUV_B'],
            'cantidad_femenino': 17,
            'cantidad_masculino': 18
        },
        {
            'distancia': '3K',
            'cantidad': 65,
            'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B'],
            'cantidad_femenino': 32,
            'cantidad_masculino': 33
        }
    ]
    
    # 3. Generar configuración
    config = gen.generar_distribucion_automatica(
        total_nadadores=TOTAL_NADADORES,
        distancias_config=distancias_config,
        usar_todas_categorias=False
    )
    
    # 4. Generar tags
    gen.generar_lote_carreras(config)
    
    # 5. Exportar
    gen.exportar_para_writer('epcs_exactos.txt')
    gen.exportar_csv('tags_exactos.csv')
    gen.exportar_json('tags_exactos.json')
    gen.imprimir_resumen()
    
    print(f"\n✅ Se generaron {len(gen.tags_generados)} tags")
    print(f"   • 2K: {sum(1 for t in gen.tags_generados if t['distancia_codigo'] == '2K')} tags")
    print(f"   • 3K: {sum(1 for t in gen.tags_generados if t['distancia_codigo'] == '3K')} tags")
    
    return gen


def ejemplo_simple_100_tags():
    """
    Ejemplo ultra-simple: 100 tags distribuidos automáticamente
    """
    gen = EPCGenerator(prefijo_evento="2026")
    
    # Una sola carrera, todas las categorías, 100 tags
    config = gen.generar_distribucion_automatica(
        total_nadadores=100,
        distancias_config=[
            {
                'distancia': '2K',
                'cantidad': 100,
                'cantidad_femenino': 50,
                'cantidad_masculino': 50
            }
        ],
        usar_todas_categorias=True
    )
    
    gen.generar_lote_carreras(config)
    gen.exportar_para_writer('100_tags.txt')
    gen.exportar_csv('100_tags.csv')
    gen.imprimir_resumen()
    
    return gen


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def _pedir_total_nadadores(mensaje="¿Cuántos nadadores en total?"):
    """Pide el total de nadadores hasta obtener un número válido (tú decides el número)."""
    while True:
        inp = input(f"\n{mensaje} [Enter=100]: ").strip()
        if not inp:
            inp = "100"
        if inp.isdigit():
            n = int(inp)
            if n > 0:
                return n
        print("  ⚠ Escribe un número entero mayor que 0.")


def _pedir_femenino_masculino(total: int, etiqueta: str = ""):
    """
    Pide cantidad femenino y masculino; verifica que sumen total.
    Si no suman, muestra verificación y vuelve a pedir hasta que coincida.
    Retorna (cant_femenino, cant_masculino).
    """
    default_f = total // 2
    default_m = total - default_f
    while True:
        inp_f = input(f"  Cantidad FEMENINO{etiqueta} [{default_f}]: ").strip()
        inp_m = input(f"  Cantidad MASCULINO{etiqueta} [{default_m}]: ").strip()
        cant_f = int(inp_f) if inp_f.isdigit() else default_f
        cant_m = int(inp_m) if inp_m.isdigit() else default_m
        suma = cant_f + cant_m
        print(f"  → Verificación: Femenino ({cant_f}) + Masculino ({cant_m}) = {suma}", end="")
        if suma == total:
            print(" ✓")
            return cant_f, cant_m
        print(f"  ✗ (debe ser {total})")
        print("  Vuelve a ingresar las cantidades.\n")


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║  GENERADOR DE CÓDIGOS EPC - COMPETENCIAS DE NATACIÓN            ║")
    print("║  Sistema FECNA - Tags RFID UHF                                  ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")

    print("\n🎯 Selecciona el modo de generación:")
    print("\n1. Manual     - Define exactamente cada categoría (configurar_evento_ejemplo)")
    print("2. Simple     - Tú dices cuántos nadadores; una sola distancia, 50% F / 50% M")
    print("3. Cantidades - Tú dices total y cantidad por distancia; F/M por carrera con verificación\n")

    modo = input("Selecciona modo (1/2/3) [Enter=3]: ").strip() or "3"

    if modo == "1":
        print("\n📋 Modo MANUAL - Usando configuración de ejemplo predefinida")
        generador = configurar_evento_ejemplo()
    elif modo == "2":
        print("\n⚡ Modo SIMPLE")
        total_nadadores = _pedir_total_nadadores("¿Cuántos nadadores (tags) quieres generar?")
        print(f"\n📊 Total: {total_nadadores} nadadores (una sola distancia, 50% F / 50% M)")
        config = [
            {
                'distancia': '2K',
                'cantidad': total_nadadores,
                'cantidad_femenino': total_nadadores // 2,
                'cantidad_masculino': total_nadadores - total_nadadores // 2
            }
        ]
        generador = EPCGenerator(prefijo_evento="2026")
        generador.generar_distribucion_automatica(
            total_nadadores=total_nadadores,
            distancias_config=config,
            usar_todas_categorias=True
        )
        generador.generar_lote_carreras(config)
    elif modo == "3":
        print("\n🎯 Modo CANTIDADES EXACTAS")

        total_nadadores = _pedir_total_nadadores("¿Cuántos nadadores en total?")
        print(f"\n📊 Total: {total_nadadores} nadadores")
        num_dist = input("¿Cuántas distancias? (1 o 2) [2]: ").strip()
        num_distancias = 2 if num_dist != "1" else 1

        if num_distancias == 1:
            dist = input("\n¿Qué distancia? (1K/2K/3K/5K) [2K]: ").strip().upper() or "2K"
            print(f"\nPara {dist} ({total_nadadores} nadadores):")
            cant_f, cant_m = _pedir_femenino_masculino(total_nadadores)
            config_dist = [
                {'distancia': dist, 'cantidad': total_nadadores, 'cantidad_femenino': cant_f, 'cantidad_masculino': cant_m}
            ]
        else:
            print("\nCarrera 1:")
            dist1 = input("  Distancia (1K/2K/3K/5K) [2K]: ").strip().upper() or "2K"
            while True:
                cant1_inp = input(f"  Cantidad de nadadores en {dist1} (resto irá a carrera 2): ").strip()
                cant1 = int(cant1_inp) if cant1_inp.isdigit() else 0
                if 0 < cant1 < total_nadadores:
                    break
                print(f"  ⚠ Debe ser un número entre 1 y {total_nadadores - 1}")
            cant2 = total_nadadores - cant1
            print(f"  → Carrera 2 tendrá {cant2} nadadores.")
            print(f"\n  Género para {dist1} ({cant1} nadadores):")
            cant_f1, cant_m1 = _pedir_femenino_masculino(cant1, f" en {dist1}")
            print(f"\nCarrera 2:")
            dist2 = input("  Distancia (1K/2K/3K/5K) [3K]: ").strip().upper() or "3K"
            print(f"  Género para {dist2} ({cant2} nadadores):")
            cant_f2, cant_m2 = _pedir_femenino_masculino(cant2, f" en {dist2}")
            config_dist = [
                {'distancia': dist1, 'cantidad': cant1, 'cantidad_femenino': cant_f1, 'cantidad_masculino': cant_m1,
                 'categorias_enfoque': ['INF_A', 'INF_B', 'JUV_A', 'JUV_B']},
                {'distancia': dist2, 'cantidad': cant2, 'cantidad_femenino': cant_f2, 'cantidad_masculino': cant_m2,
                 'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B']}
            ]

        generador = EPCGenerator(prefijo_evento="2026")
        config = generador.generar_distribucion_automatica(
            total_nadadores=total_nadadores,
            distancias_config=config_dist,
            usar_todas_categorias=True
        )
        generador.generar_lote_carreras(config)
    else:
        print("Opción no válida. Usando Modo 3 (Cantidades).")
        modo = "3"
        total_nadadores = _pedir_total_nadadores("¿Cuántos nadadores en total?")
        print(f"\n📊 Total: {total_nadadores} nadadores")
        num_distancias = 2 if input("¿Cuántas distancias? (1 o 2) [2]: ").strip() != "1" else 1
        if num_distancias == 1:
            dist = input("\n¿Qué distancia? (1K/2K/3K/5K) [2K]: ").strip().upper() or "2K"
            print(f"\nPara {dist} ({total_nadadores} nadadores):")
            cant_f, cant_m = _pedir_femenino_masculino(total_nadadores)
            config_dist = [{'distancia': dist, 'cantidad': total_nadadores, 'cantidad_femenino': cant_f, 'cantidad_masculino': cant_m}]
        else:
            dist1 = input("\nCarrera 1 - Distancia (1K/2K/3K/5K) [2K]: ").strip().upper() or "2K"
            while True:
                cant1_inp = input(f"  Cantidad en {dist1}: ").strip()
                cant1 = int(cant1_inp) if cant1_inp.isdigit() else 0
                if 0 < cant1 < total_nadadores:
                    break
                print(f"  ⚠ Entre 1 y {total_nadadores - 1}")
            cant2 = total_nadadores - cant1
            dist2 = input(f"\nCarrera 2 - Distancia [3K]: ").strip().upper() or "3K"
            print(f"  Género {dist1} ({cant1}):")
            cant_f1, cant_m1 = _pedir_femenino_masculino(cant1, f" en {dist1}")
            print(f"  Género {dist2} ({cant2}):")
            cant_f2, cant_m2 = _pedir_femenino_masculino(cant2, f" en {dist2}")
            config_dist = [
                {'distancia': dist1, 'cantidad': cant1, 'cantidad_femenino': cant_f1, 'cantidad_masculino': cant_m1, 'categorias_enfoque': ['INF_A', 'INF_B', 'JUV_A', 'JUV_B']},
                {'distancia': dist2, 'cantidad': cant2, 'cantidad_femenino': cant_f2, 'cantidad_masculino': cant_m2, 'categorias_enfoque': ['MAY_A', 'MAY_B', 'MAS_A', 'MAS_B']}
            ]
        generador = EPCGenerator(prefijo_evento="2026")
        config = generador.generar_distribucion_automatica(total_nadadores=total_nadadores, distancias_config=config_dist, usar_todas_categorias=True)
        generador.generar_lote_carreras(config)

    # Mostrar resultados
    generador.imprimir_resumen()
    generador.imprimir_muestra(cantidad=10)
    
    # Exportar archivos
    print("\n📁 Exportando archivos...")
    generador.exportar_para_writer('epcs_para_writer.txt')
    generador.exportar_csv('tags_para_registro.csv')
    generador.exportar_json('tags_completo.json')
    
    print("\n✅ Proceso completado!")
    total_gen = len(generador.tags_generados)
    print(f"📊 Total de tags generados: {total_gen}")

    # Verificación: Femenino + Masculino = Total
    cuenta_f = sum(1 for t in generador.tags_generados if t.get('genero_codigo') == 'F')
    cuenta_m = sum(1 for t in generador.tags_generados if t.get('genero_codigo') == 'M')
    suma_gen = cuenta_f + cuenta_m
    ok = "✓" if suma_gen == total_gen else "✗"
    print(f"\n📋 Verificación género: Femenino ({cuenta_f}) + Masculino ({cuenta_m}) = {suma_gen} {ok}")

    # Mostrar distribución por distancia
    por_dist = {}
    for tag in generador.tags_generados:
        dist = tag['distancia_codigo']
        por_dist[dist] = por_dist.get(dist, 0) + 1

    if len(por_dist) > 1:
        print("\n📏 Distribución por distancia:")
        for dist, cant in sorted(por_dist.items()):
            print(f"   • {dist}: {cant} tags")
    
    print("\n💡 Archivos generados:")
    print("   • epcs_para_writer.txt  → Copiar al writer RFID")
    print("   • tags_para_registro.csv → Para imprimir y registro")
    print("   • tags_completo.json     → Backup con metadata completa")
    
    print("\n" + "="*70)
    print("CATEGORÍAS FECNA DISPONIBLES:")
    print("="*70)
    for codigo, (nombre, min_edad, max_edad) in EPCGenerator.CATEGORIAS_FECNA.items():
        print(f"  {codigo:10s} → {nombre:20s} ({min_edad}-{max_edad} años)")
    
    print("\n" + "="*70)
    print("💡 TIPS:")
    print("   • Modo 2 (Simple): Una distancia, 50% F / 50% M")
    print("   • Modo 3 (Cantidades): Cantidad por distancia y F/M con verificación")
    print("   • Para control total: Edita configurar_evento_ejemplo()")
    print("="*70)
