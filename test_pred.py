# Usar credenciales por defecto de la sesión o del entorno
from google.cloud import bigquery
from agent.bq_client import PROJECT, DATASET

client = bigquery.Client()

codigo = "432115"
sql = f"""
WITH annual_data AS (
  SELECT
    EXTRACT(YEAR FROM fecha_de_firma) AS anio,
    COUNT(*) AS total_contratos,
    SUM(valor_del_contrato) AS total_valor
  FROM
    `{PROJECT}.{DATASET}.contratos_electronicos`
  WHERE
    (codigo_de_categoria_principal = '{codigo}' OR STARTS_WITH(codigo_de_categoria_principal, '{codigo}'))
    AND fecha_de_firma IS NOT NULL
    AND EXTRACT(YEAR FROM fecha_de_firma) BETWEEN 2018 AND 2025
  GROUP BY
    anio
)
SELECT
  anio,
  total_contratos,
  total_valor,
  (SELECT COVAR_POP(total_valor, anio) / NULLIF(VAR_POP(anio), 0) FROM annual_data) AS slope_valor,
  (SELECT AVG(total_valor) - (COVAR_POP(total_valor, anio) / NULLIF(VAR_POP(anio), 0)) * AVG(anio) FROM annual_data) AS intercept_valor,
  (SELECT COALESCE(CORR(total_valor, anio) * CORR(total_valor, anio), 0) FROM annual_data) AS r2_valor,
  (SELECT COVAR_POP(total_contratos, anio) / NULLIF(VAR_POP(anio), 0) FROM annual_data) AS slope_contratos,
  (SELECT AVG(total_contratos) - (COVAR_POP(total_contratos, anio) / NULLIF(VAR_POP(anio), 0)) * AVG(anio) FROM annual_data) AS intercept_contratos,
  (SELECT COALESCE(CORR(total_contratos, anio) * CORR(total_contratos, anio), 0) FROM annual_data) AS r2_contratos
FROM
  annual_data
ORDER BY
  anio ASC
"""

print("Running query...")
try:
    job = client.query(sql)
    rows = list(job.result(max_results=100))
    print(f"Results ({len(rows)}):")
    for r in rows:
        print(dict(r))
except Exception as e:
    print("Error:", e)
