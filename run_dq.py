from google.cloud import bigquery
import os
import json

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

queries = {
    "contratos_valor_cero_negativo": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.contratos_electronicos` 
        WHERE valor_del_contrato <= 0
    """,
    "contratos_valor_extremo": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.contratos_electronicos` 
        WHERE valor_del_contrato > 1000000000000 -- 1 billon
    """,
    "contratos_fechas_raras": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.contratos_electronicos`
        WHERE EXTRACT(YEAR FROM SAFE_CAST(fecha_de_firma AS TIMESTAMP)) < 2000 
           OR EXTRACT(YEAR FROM SAFE_CAST(fecha_de_firma AS TIMESTAMP)) > 2100
    """,
    "procesos_precio_base_placeholder": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.procesos_contratacion`
        WHERE SAFE_CAST(precio_base AS FLOAT64) <= 1000
    """,
    "facturas_valor_negativo": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.facturas`
        WHERE SAFE_CAST(valor_total AS FLOAT64) < 0
    """,
    "facturas_duplicadas": """
        WITH facturas_unicas AS (
            SELECT id_contrato, numero_de_factura, COUNT(*) as c
            FROM `odin-v2-495523.secop.facturas`
            GROUP BY id_contrato, numero_de_factura
        )
        SELECT COUNT(*) as c FROM facturas_unicas WHERE c > 1
    """,
    "adiciones_valor_cero": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.adiciones`
        WHERE valor_adicion = 0
    """,
    "adiciones_fechas_futuras": """
        SELECT COUNT(*) as c FROM `odin-v2-495523.secop.adiciones`
        WHERE EXTRACT(YEAR FROM SAFE_CAST(fecha_adicion AS TIMESTAMP)) > 2100
    """
}

results = {}
for name, q in queries.items():
    try:
        res = list(client.query(q).result())
        results[name] = res[0].c
    except Exception as e:
        results[name] = str(e)

with open("dq_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Data quality checks completed. Results in dq_results.json.")
