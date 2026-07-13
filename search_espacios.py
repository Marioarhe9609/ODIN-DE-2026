import os
from google.cloud import bigquery

# Set environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def search():
    query_str = """
    SELECT proveedor_adjudicado, documento_proveedor, COUNT(*) as cnt, SUM(CAST(valor_del_contrato AS INT64)) as total_val 
    FROM `odin-v2-495523.secop.contratos_electronicos` 
    WHERE LOWER(proveedor_adjudicado) LIKE '%espacios y redes%' 
    GROUP BY proveedor_adjudicado, documento_proveedor
    """
    print("Running query...")
    query_job = client.query(query_str)
    results = query_job.result()
    print("Results:")
    for row in results:
        print(row)

if __name__ == "__main__":
    search()
