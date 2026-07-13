import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def analyze():
    # 1. Top categories
    q_cats = """
    SELECT codigo_de_categoria_principal, COUNT(*) as cnt, SUM(CAST(valor_del_contrato AS INT64)) as total_val
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE documento_proveedor = '830144531'
    GROUP BY codigo_de_categoria_principal
    ORDER BY cnt DESC
    LIMIT 10
    """
    
    # 2. Top entities
    q_ents = """
    SELECT nombre_entidad, COUNT(*) as cnt, SUM(CAST(valor_del_contrato AS INT64)) as total_val
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE documento_proveedor = '830144531'
    GROUP BY nombre_entidad
    ORDER BY cnt DESC
    LIMIT 10
    """
    
    # 3. Top departments
    q_deps = """
    SELECT departamento_entidad, COUNT(*) as cnt, SUM(CAST(valor_del_contrato AS INT64)) as total_val
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE documento_proveedor = '830144531'
    GROUP BY departamento_entidad
    ORDER BY cnt DESC
    LIMIT 5
    """

    print("--- TOP CATEGORIES ---")
    for r in client.query(q_cats).result():
        print(r)
        
    print("\n--- TOP ENTITIES ---")
    for r in client.query(q_ents).result():
        print(r)
        
    print("\n--- TOP DEPARTMENTS ---")
    for r in client.query(q_deps).result():
        print(r)

if __name__ == "__main__":
    analyze()
