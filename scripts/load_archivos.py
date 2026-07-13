"""Load SECOP II document tables using CSV export (much faster than JSON API)."""
import subprocess
import os
import sys
import time

PROJECT = "odin-v2-495523"
DATASET = "secop"

# Dataset ID -> table name
DATASETS = [
    ("dmgg-8hin", "archivos_2025", "Archivos Desde 2025"),
    ("3skv-9na7", "archivos_2023", "Archivos Historico 2023"),
    ("kgcd-kt7i", "archivos_2022", "Archivos Historico 2022"),
]

# Use workspace for temp files instead of /tmp
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(WORKSPACE, "scripts", "temp_csv")
os.makedirs(TEMP_DIR, exist_ok=True)


def download_csv(dataset_id, output_file):
    """Download CSV from datos.gov.co using curl (streaming)."""
    url = f"https://www.datos.gov.co/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
    print(f"  Downloading CSV from {url}...")
    print(f"  Output: {output_file}")
    
    result = subprocess.run(
        ["curl", "-L", "-o", output_file, "--progress-bar", url],
        capture_output=False,
        timeout=7200,  # 2 hour timeout
    )
    
    if result.returncode != 0:
        print(f"  ERROR: curl failed with code {result.returncode}")
        return False
    
    size = os.path.getsize(output_file)
    print(f"  Downloaded: {size / 1e9:.2f} GB")
    return True


def load_to_bq(csv_file, table_name):
    """Load CSV file to BigQuery using bq load CLI."""
    table_ref = f"{PROJECT}:{DATASET}.{table_name}"
    print(f"  Loading {csv_file} -> {table_ref}...")
    
    result = subprocess.run([
        "bq", "load",
        "--source_format=CSV",
        "--autodetect",
        "--skip_leading_rows=1",
        "--max_bad_records=1000",
        "--replace",  # Replace existing data
        table_ref,
        csv_file,
    ], capture_output=True, text=True, timeout=3600)
    
    if result.returncode != 0:
        print(f"  ERROR: bq load failed: {result.stderr}")
        return False
    
    print(f"  Loaded successfully!")
    return True


def verify_table(table_name):
    """Check row count."""
    result = subprocess.run([
        "bq", "query", "--nouse_legacy_sql", "--format=csv",
        f"SELECT COUNT(*) as n FROM `{PROJECT}.{DATASET}.{table_name}`"
    ], capture_output=True, text=True, timeout=60)
    print(f"  {table_name}: {result.stdout.strip()}")


def create_unified_view():
    """Create the archivos_secop unified view."""
    sql = f"""
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
    result = subprocess.run([
        "bq", "query", "--nouse_legacy_sql",
        sql
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("  Unified view archivos_secop created!")
    else:
        print(f"  ERROR creating view: {result.stderr}")


def main():
    print("=== SECOP II Document Archives Loader ===\n")
    
    for dataset_id, table_name, label in DATASETS:
        print(f"\n{'='*50}")
        print(f"[{label}] {dataset_id} -> {table_name}")
        print(f"{'='*50}")
        
        csv_file = os.path.join(TEMP_DIR, f"{table_name}.csv")
        
        # Step 1: Download
        t0 = time.time()
        if not download_csv(dataset_id, csv_file):
            continue
        print(f"  Download took {(time.time()-t0)/60:.1f} min")
        
        # Step 2: Load to BigQuery
        t1 = time.time()
        if not load_to_bq(csv_file, table_name):
            continue
        print(f"  Load took {(time.time()-t1)/60:.1f} min")
        
        # Step 3: Verify
        verify_table(table_name)
        
        # Step 4: Cleanup
        os.remove(csv_file)
        print(f"  Cleaned up {csv_file}")
    
    # Create unified view
    print(f"\n{'='*50}")
    print("Creating unified view...")
    create_unified_view()
    
    print(f"\n=== ALL DONE ===")


if __name__ == "__main__":
    main()
