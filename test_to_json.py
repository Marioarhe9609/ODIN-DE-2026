from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

sql = """
SELECT 'TEST' as type, TO_JSON_STRING(t) as json_val
FROM `odin-v2-495523.secop.v_anticorr_monopolista` t
LIMIT 1
"""
try:
    res = list(client.query(sql).result())
    print("SUCCESS!")
    print("JSON val:", res[0]['json_val'])
except Exception as e:
    print("FAILED with exception:")
    print(e)
