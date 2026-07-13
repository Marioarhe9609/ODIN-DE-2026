# Usar credenciales por defecto de la sesión o del entorno
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DATASET = "secop"
client = bigquery.Client()

sql = f"""
SELECT * FROM `{PROJECT}.{DATASET}.grupos_proveedores` 
WHERE nombre_grupo LIKE '%DAING SENA%' OR nombre_participante LIKE '%DAING SENA%'
"""
print("Running query...")
try:
    rows = list(client.query(sql).result())
    print("Found rows:", len(rows))
    for r in rows:
        print(dict(r))
except Exception as e:
    print("Error:", e)
