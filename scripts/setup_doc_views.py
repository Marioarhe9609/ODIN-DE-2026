"""Check loaded archive tables and create unified view + missing table."""
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DATASET = "secop"
client = bigquery.Client(project=PROJECT)

# Check existing
for t in ["archivos_2025", "archivos_2023", "archivos_2022"]:
    try:
        tbl = client.get_table(f"{PROJECT}.{DATASET}.{t}")
        print(f"{t}: {tbl.num_rows:,} rows, {tbl.num_bytes/1e9:.2f} GB")
    except Exception as e:
        print(f"{t}: NOT FOUND - {e}")

# Create unified view with whatever tables exist
print("\nCreating unified view...")

def get_select_sql(table_name):
    return f"""
    SELECT 
      CAST(n_mero_de_contrato AS STRING) as n_mero_de_contrato,
      CAST(id_documento AS INT64) as id_documento,
      CAST(proceso AS STRING) as proceso,
      CAST(nombre_archivo AS STRING) as nombre_archivo,
      CAST(tamanno_archivo AS FLOAT64) as tamanno_archivo,
      CAST(extensi_n AS STRING) as extensi_n,
      CAST(descripci_n AS STRING) as descripci_n,
      SAFE_CAST(fecha_carga AS TIMESTAMP) as fecha_carga,
      CAST(entidad AS STRING) as entidad,
      CAST(nit_entidad AS STRING) as nit_entidad,
      CAST(url_descarga_documento AS STRING) as url_descarga_documento
    FROM `{PROJECT}.{DATASET}.{table_name}`
    """

tables_to_union = ["archivos_2025", "archivos_2023"]

# Check if archivos_2022 exists
try:
    client.get_table(f"{PROJECT}.{DATASET}.archivos_2022")
    tables_to_union.append("archivos_2022")
except Exception:
    print("archivos_2022 not loaded yet, view will use 2025+2023 only")

select_clauses = [get_select_sql(t) for t in tables_to_union]
union_sql = "\nUNION ALL\n".join(select_clauses)
view_sql = f"CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.archivos_secop` AS\n{union_sql}"

client.query(view_sql).result()
print("View archivos_secop created!")

# Now create the 3 anticorrupcion views based on documents
print("\nCreating anticorrupcion document views...")

# View 1: Contracts without ANY documents
v1 = f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.v_anticorr_sin_documentos` AS
SELECT 
  c.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  c.fecha_de_firma,
  c.modalidad_de_contratacion
FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
LEFT JOIN `{PROJECT}.{DATASET}.archivos_secop` d 
  ON d.n_mero_de_contrato = c.id_contrato
WHERE d.n_mero_de_contrato IS NULL
  AND c.valor_del_contrato > 50000000
  AND c.fecha_de_firma IS NOT NULL
"""
client.query(v1).result()
print("  v_anticorr_sin_documentos created!")

# View 2: Documents uploaded >90 days AFTER contract ended
v2 = f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.v_anticorr_docs_tardios` AS
SELECT 
  d.n_mero_de_contrato as id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  CAST(c.fecha_de_fin_del_contrato AS DATE) as fecha_fin_contrato,
  COUNT(*) as docs_tardios,
  MAX(CAST(d.fecha_carga AS DATE)) as ultima_carga_tardia,
  MAX(DATE_DIFF(CAST(d.fecha_carga AS DATE), CAST(c.fecha_de_fin_del_contrato AS DATE), DAY)) as dias_retraso_max
FROM `{PROJECT}.{DATASET}.archivos_secop` d
JOIN `{PROJECT}.{DATASET}.contratos_electronicos` c 
  ON d.n_mero_de_contrato = c.id_contrato
WHERE c.fecha_de_fin_del_contrato IS NOT NULL
  AND CAST(d.fecha_carga AS DATE) > CAST(c.fecha_de_fin_del_contrato AS DATE)
  AND DATE_DIFF(CAST(d.fecha_carga AS DATE), CAST(c.fecha_de_fin_del_contrato AS DATE), DAY) > 90
GROUP BY 1,2,3,4,5
HAVING COUNT(*) > 5
"""
client.query(v2).result()
print("  v_anticorr_docs_tardios created!")

# View 3: Contracts missing critical documents (estudios previos)
v3 = f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.v_anticorr_docs_faltantes` AS
SELECT 
  c.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  c.modalidad_de_contratacion,
  c.fecha_de_firma,
  COUNTIF(UPPER(d.nombre_archivo) LIKE '%ESTUDIO%PREVIO%') as tiene_estudios_previos,
  COUNTIF(UPPER(d.nombre_archivo) LIKE '%CDP%') as tiene_cdp,
  COUNTIF(UPPER(d.nombre_archivo) LIKE '%ACTA%INICIO%') as tiene_acta_inicio,
  COUNTIF(UPPER(d.nombre_archivo) LIKE '%POLIZA%' OR UPPER(d.nombre_archivo) LIKE '%GARANTIA%') as tiene_poliza,
  COUNT(*) as total_docs
FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
LEFT JOIN `{PROJECT}.{DATASET}.archivos_secop` d 
  ON d.n_mero_de_contrato = c.id_contrato
WHERE c.valor_del_contrato > 100000000
  AND c.fecha_de_firma IS NOT NULL
  AND c.modalidad_de_contratacion NOT LIKE '%irecta%'
GROUP BY 1,2,3,4,5,6
HAVING COUNTIF(UPPER(d.nombre_archivo) LIKE '%ESTUDIO%PREVIO%') = 0
    OR COUNTIF(UPPER(d.nombre_archivo) LIKE '%CDP%') = 0
"""
client.query(v3).result()
print("  v_anticorr_docs_faltantes created!")

print("\nAll done! 3 new document-based anticorruption views created.")
