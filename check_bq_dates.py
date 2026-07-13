from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

sql = """
SELECT 
    MAX(fecha_de_publicacion_del_proceso) as max_date,
    CURRENT_DATE() as current_bq_date,
    COUNT(*) as total_rows
FROM `odin-v2-495523.secop.procesos_contratacion`
"""

try:
    results = list(client.query(sql).result())
    for row in results:
        print(f"Max Date: {row.max_date}")
        print(f"Current BQ Date: {row.current_bq_date}")
        print(f"Total Rows: {row.total_rows}")
except Exception as e:
    print(f"Error: {e}")
