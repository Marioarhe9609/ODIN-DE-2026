import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def check():
    sql = """
    SELECT proveedor_adjudicado, fecha_de_firma, valor_del_contrato
    FROM `odin-v2-495523.secop.contratos_electronicos`
    WHERE LOWER(proveedor_adjudicado) LIKE '%compumax%'
      AND EXTRACT(YEAR FROM fecha_de_firma) = 2025
    LIMIT 10
    """
    print("Checking BQ...")
    rows = list(client.query(sql).result())
    print(f"Found {len(rows)} contracts in 2025.")
    for r in rows:
        print(dict(r))

if __name__ == "__main__":
    check()
