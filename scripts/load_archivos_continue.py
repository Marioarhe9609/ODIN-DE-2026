"""Load missing archivos_2022 table using Socrata JSON API with BQ load jobs."""
import requests
import json
import os
import time
import tempfile
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DATASET = "secop"
client = bigquery.Client(project=PROJECT)

SCHEMA = [
    bigquery.SchemaField("n_mero_de_contrato", "STRING"),
    bigquery.SchemaField("id_documento", "STRING"),
    bigquery.SchemaField("proceso", "STRING"),
    bigquery.SchemaField("nombre_archivo", "STRING"),
    bigquery.SchemaField("tamanno_archivo", "STRING"),
    bigquery.SchemaField("extensi_n", "STRING"),
    bigquery.SchemaField("descripci_n", "STRING"),
    bigquery.SchemaField("fecha_carga", "STRING"),
    bigquery.SchemaField("entidad", "STRING"),
    bigquery.SchemaField("nit_entidad", "STRING"),
]

BATCH = 50000
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(WORKSPACE, "scripts", "temp_csv")
os.makedirs(TEMP_DIR, exist_ok=True)


def load_dataset(table_name, dataset_id, append=True):
    table_ref = f"{PROJECT}.{DATASET}.{table_name}"
    
    # Create table if needed
    try:
        tbl = client.get_table(table_ref)
        current = tbl.num_rows
        print(f"  {table_name} exists with {current:,} rows")
    except Exception:
        table = bigquery.Table(table_ref, schema=SCHEMA)
        client.create_table(table)
        print(f"  Created table {table_name}")
        current = 0
    
    offset = current if append else 0
    total = current
    
    while True:
        url = f"https://www.datos.gov.co/resource/{dataset_id}.json?$limit={BATCH}&$offset={offset}&$order=:id"
        print(f"  Fetching offset {offset:,}...", end=" ", flush=True)
        
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=180)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    print(f"retry {attempt+1}...", end=" ", flush=True)
                    time.sleep(10)
                else:
                    print(f"FAILED: {e}")
                    return total
        
        if not data:
            print("no more data")
            break
        
        # Clean and write to temp file
        tmpfile = os.path.join(TEMP_DIR, f"batch_{table_name}.jsonl")
        with open(tmpfile, "w", encoding="utf-8") as f:
            for row in data:
                clean = {k: str(v or "") for k, v in row.items() if k in [s.name for s in SCHEMA]}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
        
        # Load to BQ
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            max_bad_records=100,
        )
        
        with open(tmpfile, "rb") as f:
            job = client.load_table_from_file(f, table_ref, job_config=job_config)
        job.result()
        
        os.remove(tmpfile)
        total += len(data)
        offset += BATCH
        print(f"loaded {len(data)} -> total: {total:,}")
        
        if len(data) < BATCH:
            break
    
    print(f"  {table_name}: DONE with {total:,} rows")
    return total


def main():
    print("=== Loading SECOP II Document Archives ===\n")
    
    # Load archivos_2022 (missing)
    print("[1/3] archivos_2022 (kgcd-kt7i)...")
    load_dataset("archivos_2022", "kgcd-kt7i")
    
    # Continue loading archivos_2023 (partial)
    print("\n[2/3] archivos_2023 (3skv-9na7)...")
    load_dataset("archivos_2023", "3skv-9na7")
    
    # Continue loading archivos_2025 (partial)
    print("\n[3/3] archivos_2025 (dmgg-8hin)...")
    load_dataset("archivos_2025", "dmgg-8hin")
    
    # Update unified view to include 2022
    print("\nUpdating unified view...")
    view_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.archivos_secop` AS
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
    FROM `{PROJECT}.{DATASET}.archivos_2025`
    UNION ALL
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
    FROM `{PROJECT}.{DATASET}.archivos_2023`
    UNION ALL
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
    FROM `{PROJECT}.{DATASET}.archivos_2022`
    """
    client.query(view_sql).result()
    print("View updated!")
    
    # Final counts
    print("\n=== Final counts ===")
    for t in ["archivos_2025", "archivos_2023", "archivos_2022"]:
        try:
            tbl = client.get_table(f"{PROJECT}.{DATASET}.{t}")
            print(f"  {t}: {tbl.num_rows:,} rows")
        except:
            print(f"  {t}: not found")


if __name__ == "__main__":
    main()
