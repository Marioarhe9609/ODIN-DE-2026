"""
SECOP II Graph Model & Recommendation Engine
---------------------------------------------
Este módulo demuestra cómo conectar las tablas relacionales puras de SECOP II
almacenadas en BigQuery en una estructura de Grafo In-Memory (Red).
Esto permite realizar consultas complejas de afinidad, análisis de caminos (paths)
y recomendaciones predictivas que con SQL relacional puro serían sumamente costosas o complejas.

Arquitectura del Grafo:
- Nodos (Types):
  * PROVEEDOR (Identificado por NIT/Documento)
  * ENTIDAD (Identificado por Nombre de Entidad)
  * CATEGORIA (Identificado por Código UNSPSC)
  * PROCESO_ACTIVO (Identificado por ID de Proceso)

- Bordes / Relaciones (Edges):
  * PROVEEDOR --[GANÓ (valor, fecha)]--> ENTIDAD
  * PROVEEDOR --[EXPERTO_EN]--> CATEGORIA
  * ENTIDAD --[PUBLICA]--> PROCESO_ACTIVO
  * PROCESO_ACTIVO --[CLASIFICADO_EN]--> CATEGORIA
"""

import os
from google.cloud import bigquery

# Configuración del entorno
os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

class SecopGraph:
    def __init__(self):
        self.nodes = {}  # id -> {type, attributes}
        self.edges = []  # list of (source, target, type, attributes)
        
    def add_node(self, node_id, node_type, **attrs):
        self.nodes[node_id] = {
            'type': node_type,
            'attrs': attrs
        }
        
    def add_edge(self, source, target, edge_type, **attrs):
        self.edges.append({
            'source': source,
            'target': target,
            'type': edge_type,
            'attrs': attrs
        })
        
    def get_neighbors(self, node_id, edge_type=None):
        """Retorna los vecinos directos y el tipo de relación."""
        neighbors = []
        for e in self.edges:
            if e['source'] == node_id:
                if edge_type is None or e['type'] == edge_type:
                    neighbors.append((e['target'], e['type'], e['attrs']))
            elif e['target'] == node_id:
                if edge_type is None or e['type'] == edge_type:
                    neighbors.append((e['source'], e['type'], e['attrs']))
        return neighbors

    def find_shortest_paths(self, start_node, end_node, max_depth=3):
        """Implementa una búsqueda en anchura (BFS) para encontrar caminos en el Grafo."""
        if start_node not in self.nodes or end_node not in self.nodes:
            return []
            
        queue = [[(start_node, None, None)]]
        visited = set()
        paths = []
        
        while queue:
            path = queue.pop(0)
            node = path[-1][0]
            
            if len(path) > max_depth + 1:
                continue
                
            if node == end_node:
                paths.append(path)
                continue
                
            if node not in visited:
                visited.add(node)
                # Obtener vecinos
                for neighbor, rel_type, attrs in self.get_neighbors(node):
                    new_path = list(path)
                    new_path.append((neighbor, rel_type, attrs))
                    queue.append(new_path)
        return paths

def load_graph_for_provider(nit_proveedor):
    """
    Carga de BigQuery un subgrafo centrado en el historial del proveedor y
    los procesos activos potencialmente compatibles.
    """
    g = SecopGraph()
    
    # 1. Obtener historial contractual del proveedor (Bordes de GANÓ y EXPERTO_EN)
    q_past = f"""
    SELECT 
      proveedor_adjudicado,
      documento_proveedor,
      nombre_entidad,
      codigo_de_categoria_principal,
      CAST(valor_del_contrato AS INT64) AS valor,
      fecha_de_firma
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE documento_proveedor = '{nit_proveedor}'
    """
    print("Cargando historial del proveedor desde BigQuery...")
    past_contracts = list(client.query(q_past).result())
    
    if not past_contracts:
        print("Proveedor no encontrado en contratos electrónicos.")
        return None
        
    proveedor_nombre = past_contracts[0].proveedor_adjudicado
    g.add_node(nit_proveedor, "PROVEEDOR", nombre=proveedor_nombre)
    
    categories = set()
    entities = set()
    
    for c in past_contracts:
        ent_id = c.nombre_entidad
        cat_id = c.codigo_de_categoria_principal
        
        # Agregar nodos
        g.add_node(ent_id, "ENTIDAD", nombre=ent_id)
        g.add_node(cat_id, "CATEGORIA", nombre=f"UNSPSC {cat_id}")
        
        # Relaciones
        g.add_edge(nit_proveedor, ent_id, "GANO_CONTRATO", valor=c.valor, fecha=c.fecha_de_firma)
        g.add_edge(nit_proveedor, cat_id, "EXPERTO_EN", valor=c.valor)
        
        categories.add(cat_id)
        entities.add(ent_id)
        
    print(f"Subgrafo cargado: {len(entities)} Entidades y {len(categories)} Categorías conectadas a ti.")
    
    # 2. Cargar Procesos Activos del mercado que coincidan con las categorías de experiencia del proveedor
    # Mantenemos las categorías en formato lista para BigQuery
    cat_list = "', '".join(categories)
    q_active = f"""
    SELECT 
      id_del_proceso,
      nombre_del_procedimiento AS objeto,
      nombre_entidad,
      codigo_principal_de_categoria AS unspsc,
      precio_base
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE estado_del_procedimiento IN ('Publicado', 'Abierto', 'Evaluación')
      AND fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) AS TIMESTAMP)
      AND (
        codigo_principal_de_categoria IN ('{cat_list}')
        OR REGEXP_CONTAINS(LOWER(nombre_del_procedimiento), 'internet|conectividad|enlace|redes|telecomunicac')
      )
    ORDER BY fecha_de_publicacion_del_proceso DESC
    LIMIT 100
    """
    
    print("Cargando oportunidades de procesos activos compatibles...")
    active_procs = list(client.query(q_active).result())
    
    for p in active_procs:
        proc_id = p.id_del_proceso
        ent_id = p.nombre_entidad
        cat_id = p.unspsc
        
        # Nodos
        g.add_node(proc_id, "PROCESO_ACTIVO", objeto=p.objeto, valor=p.precio_base)
        g.add_node(ent_id, "ENTIDAD", nombre=ent_id)
        if cat_id:
            g.add_node(cat_id, "CATEGORIA", nombre=f"UNSPSC {cat_id}")
            g.add_edge(proc_id, cat_id, "CLASIFICADO_EN")
            
        g.add_edge(ent_id, proc_id, "PUBLICA")
        
    print(f"Cargados {len(active_procs)} procesos activos al Grafo de afinidad.")
    return g, active_procs

def demonstrate_graph_queries(g, nit_proveedor, active_procs):
    """Muestra cómo resolver consultas de recomendación usando análisis de caminos (Paths)."""
    print("\n" + "="*60)
    print("DEMOSTRACIÓN DE CONSULTAS COMPLEJAS BASADAS EN GRAFOS")
    print("="*60)
    
    # Queremos encontrar la afinidad de cada proceso activo con el contratista 'ESPACIOS Y REDES'
    # mediante análisis de conectividad (caminos de longitud <= 3)
    recommendations = []
    
    for p in active_procs:  # Evaluamos todos los candidatos para encontrar coincidencias reales
        paths = g.find_shortest_paths(nit_proveedor, p.id_del_proceso, max_depth=3)
        if not paths:
            continue
            
        # Puntuamos el proceso de acuerdo a la riqueza de caminos que lo conectan a nosotros
        score = 0
        path_details = []
        for path in paths:
            # Un camino es una lista de tuplas (nodo, tipo_relación, atributos)
            path_len = len(path) - 1  # Número de saltos (hops)
            
            # Ejemplo de camino de longitud 2:
            # Proveedor -> GANÓ -> Entidad -> PUBLICA -> Proceso
            if path_len == 2:
                middle_node = path[1][0]
                rel_1 = path[1][1]
                rel_2 = path[2][1]
                
                if rel_1 == "GANO_CONTRATO" and rel_2 == "PUBLICA":
                    score += 15
                    path_details.append(f"Camino de Relación Histórica: Tu red empresarial se conecta con este proceso porque ya has ganado contratos directamente con la entidad compradora '{middle_node}'.")
            
            # Ejemplo de camino de longitud 2 alternativo:
            # Proveedor -> EXPERTO_EN -> Categoria -> CLASIFICADO_EN -> Proceso
            elif path_len == 2:
                middle_node = path[1][0]
                rel_1 = path[1][1]
                rel_2 = path[2][1]
                
                if rel_1 == "EXPERTO_EN" and rel_2 == "CLASIFICADO_EN":
                    score += 10
                    path_details.append(f"Camino de Capacidad Técnica: Tu red empresarial se conecta con este proceso porque compartes la especialidad en la categoría '{middle_node}'.")
                    
        if score > 0:
            recommendations.append({
                'id': p.id_del_proceso,
                'objeto': p.objeto,
                'entidad': p.nombre_entidad,
                'valor': p.precio_base,
                'score': score,
                'paths': path_details
            })
            
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\nSe encontraron {len(recommendations)} conexiones logicas de procesos recomendados.")
    for idx, rec in enumerate(recommendations[:4]):
        print(f"\n[RANK #{idx+1}] (Puntuacion en Grafo: {rec['score']} Puntos)")
        print(f"  • ID del Proceso: {rec['id']}")
        print(f"  • Entidad: {rec['entidad']}")
        print(f"  • Objeto: {rec['objeto'][:120]}...")
        print(f"  • Presupuesto: ${float(rec['valor']):,.0f} COP")
        print("  • Trazabilidad de Caminos en Grafo:")
        for path in rec['paths']:
            print(f"    - {path}")

if __name__ == "__main__":
    res = load_graph_for_provider("830144531")
    if res:
        g, active_procs = res
        demonstrate_graph_queries(g, "830144531", active_procs)
