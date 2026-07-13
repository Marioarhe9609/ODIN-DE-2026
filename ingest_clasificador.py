import os
import sys
import csv
from google.cloud import bigquery

# Set up BQ Environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

csv_path = "C:/Users/ASUS/Downloads/clasificador_de_bienes_y_servicios_v14_1(Clasificador).csv"
project_id = "odin-v2-495523"
dataset_id = "secop"
table_id = "unspsc_clasificador"

def main():
    if not os.path.exists(csv_path):
        print(f"Error: File not found at {csv_path}")
        sys.exit(1)
        
    print(f"Parsing UNSPSC CSV from {csv_path}...")
    
    rows = []
    with open(csv_path, "r", encoding="latin-1") as fp:
        # Skip first 3 lines of preamble
        for _ in range(3):
            fp.readline()
            
        # Line 4 contains column headers: "Código Segmento;Nombre Segmento;Código Familia;Nombre Familia;Código Clase;Nombre Clase;Código Producto;Nombre Producto"
        header_line = fp.readline().strip()
        print(f"Headers found: {header_line}")
        
        # Use csv reader with semicolon delimiter
        reader = csv.reader(fp, delimiter=";")
        for row in reader:
            if not row or len(row) < 8:
                continue
                
            # Clean and construct the record
            record = {
                "codigo_segmento": row[0].strip(),
                "nombre_segmento": row[1].strip(),
                "codigo_familia": row[2].strip(),
                "nombre_familia": row[3].strip(),
                "codigo_clase": row[4].strip(),
                "nombre_clase": row[5].strip(),
                "codigo_producto": row[6].strip(),
                "nombre_producto": row[7].strip()
            }
            rows.append(record)
            
    print(f"Successfully parsed {len(rows):,} UNSPSC classification records.")
    
    # Ingest into BigQuery
    client = bigquery.Client(project=project_id)
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    
    # Define Schema
    schema = [
        bigquery.SchemaField("codigo_segmento", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("nombre_segmento", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("codigo_familia", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("nombre_familia", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("codigo_clase", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("nombre_clase", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("codigo_producto", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("nombre_producto", "STRING", mode="NULLABLE"),
    ]
    
    # Create or replace table
    table = bigquery.Table(full_table_id, schema=schema)
    client.delete_table(full_table_id, not_found_ok=True)
    table = client.create_table(table)
    print(f"Created BigQuery table {full_table_id}.")
    
    # Load JSON data
    print("Uploading records to BigQuery...")
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema
    )
    
    # Chunk uploading to prevent large payload exceptions (e.g. max payload sizes)
    chunk_size = 10000
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        job = client.load_table_from_json(chunk, full_table_id, job_config=job_config)
        job.result() # Wait for job completion
        print(f"Loaded records {i:,} to {i+len(chunk):,}...")
        
    print(f"\n🎉 SUCCESS: BigQuery table {full_table_id} populated successfully with {len(rows):,} records!")

if __name__ == "__main__":
    main()
