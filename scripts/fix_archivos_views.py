"""Fix files view with explicit casts to prevent UNION ALL incompatible schemas."""
from google.cloud import bigquery
import sys

sys.stdout.reconfigure(encoding='utf-8')

import os

PROJECT = os.getenv("GCP_PROJECT_ID", "odin-v2-495523")
DATASET = os.getenv("BQ_DATASET", "secop")
client = bigquery.Client(project=PROJECT)

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
      CAST(NULL AS STRING) as url_descarga_documento
    FROM `{PROJECT}.{DATASET}.{table_name}`
    """

def run():
    print("=" * 60)
    print("FIXING DOCUMENT-BASED VIEWS IN BIGQUERY")
    print("=" * 60)
    
    tables_to_union = ["archivos_2025", "archivos_2023"]
    
    # Check if archivos_2022 exists
    try:
        client.get_table(f"{PROJECT}.{DATASET}.archivos_2022")
        tables_to_union.append("archivos_2022")
        print("Detected archivos_2022 in dataset.")
    except Exception:
        print("archivos_2022 not found or not accessible.")
        
    select_clauses = [get_select_sql(t) for t in tables_to_union]
    union_sql = "\nUNION ALL\n".join(select_clauses)
    
    view_sql = f"CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.archivos_secop` AS\n{union_sql}"
    
    print("\nCreating view archivos_secop with explicit casts...")
    try:
        client.query(view_sql).result()
        print("  [OK] view archivos_secop created successfully.")
    except Exception as e:
        print(f"  [ERR] failed to create archivos_secop: {e}")
        return
        
    # Re-create child views
    print("\nCreating child document-based views...")
    
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
    
    child_views = [
        ("v_anticorr_sin_documentos", v1),
        ("v_anticorr_docs_tardios", v2),
        ("v_anticorr_docs_faltantes", v3)
    ]
    
    for name, sql in child_views:
        try:
            client.query(sql).result()
            print(f"  [OK] view {name} created successfully.")
        except Exception as e:
            print(f"  [ERR] failed to create view {name}: {e}")
            
    print("\nUnified and child document views fixed successfully.")

if __name__ == "__main__":
    run()
