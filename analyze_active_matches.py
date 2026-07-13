import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def analyze():
    # 1. Print some object samples
    q_samples = """
    SELECT objeto_del_contrato, valor_del_contrato, nombre_entidad
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE documento_proveedor = '830144531'
    LIMIT 5
    """
    print("--- SAMPLE PAST CONTRACTS FOR ESPACIOS Y REDES ---")
    for r in client.query(q_samples).result():
        print(f"Entidad: {r.nombre_entidad} | Valor: {r.valor_del_contrato} | Objeto: {r.objeto_del_contrato[:120]}...")

    # 2. Get active/open processes in the relevant categories or entities
    # Let's search in processes_contratacion
    # Categories: '81112100', '81112101', '83121703', '83121700'
    # Or entities containing 'CENAC', 'ICANH', 'DEFENSA', 'EJERCITO'
    q_active = """
    SELECT 
      id_del_proceso,
      nombre_del_procedimiento,
      nombre_entidad,
      modalidad_de_contratacion,
      estado_del_procedimiento,
      precio_base,
      fecha_de_publicacion_del_proceso,
      codigo_principal_de_categoria,
      urlproceso
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE estado_del_procedimiento IN ('Publicado', 'Abierto', 'Evaluación')
      AND fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) AS TIMESTAMP)
      AND (
        codigo_principal_de_categoria LIKE 'V1.811121%'
        OR codigo_principal_de_categoria LIKE 'V1.831217%'
        OR REGEXP_LIKE(LOWER(nombre_entidad), 'cenac|icanh|defensa|ejercito')
      )
    ORDER BY fecha_de_publicacion_del_proceso DESC
    LIMIT 50
    """
    
    print("\n--- ACTIVE/RECENT RELEVANT PROCESSES ---")
    active_rows = list(client.query(q_active).result())
    print(f"Found {len(active_rows)} active/recent relevant processes.")
    for idx, r in enumerate(active_rows[:10]):
        print(f"[{idx+1}] Entidad: {r.nombre_entidad} | Cat: {r.codigo_principal_de_categoria} | Valor: {r.precio_base} | Objeto: {r.nombre_del_procedimiento[:120]}...")

    # Let's save them so we can do a scoring logic in Python
    return active_rows

if __name__ == "__main__":
    analyze()
