from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

# List datasets
datasets = list(client.list_datasets())
print("Datasets in project:")
for ds in datasets:
    print(f"- {ds.dataset_id}")

# Let's count ICANH contracts in 2026 in 'secop.contratos_electronicos'
query_1 = """
SELECT COUNT(*) as count 
FROM `odin-v2-495523.secop.contratos_electronicos` 
WHERE EXTRACT(YEAR FROM fecha_de_firma) = 2026 
  AND LOWER(nombre_entidad) LIKE '%icanh%'
"""
try:
    res = list(client.query(query_1).result())
    print("secop.contratos_electronicos count:", res[0]['count'])
except Exception as e:
    print("Query 1 error:", e)

# Let's also check other datasets if any
for ds in datasets:
    ds_id = ds.dataset_id
    if ds_id == "secop":
        continue
    query_x = f"""
    SELECT COUNT(*) as count 
    FROM `odin-v2-495523.{ds_id}.contratos_electronicos` 
    WHERE EXTRACT(YEAR FROM fecha_de_firma) = 2026 
      AND LOWER(nombre_entidad) LIKE '%icanh%'
    """
    try:
        res = list(client.query(query_x).result())
        print(f"{ds_id}.contratos_electronicos count:", res[0]['count'])
    except Exception:
        pass
