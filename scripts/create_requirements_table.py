import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from google.cloud import bigquery

client = bigquery.Client(project="odin-v2-495523")
table_id = "odin-v2-495523.secop.procesos_requisitos"

# Create the table schema
schema = [
    bigquery.SchemaField("id_del_proceso", "STRING", mode="REQUIRED", description="ID unico del proceso (CO1.REQ.XXX)"),
    bigquery.SchemaField("experiencia_unspsc", "STRING", mode="REPEATED", description="Codigos UNSPSC exigidos para experiencia"),
    bigquery.SchemaField("experiencia_minima_cop", "NUMERIC", mode="NULLABLE", description="Valor minimo de experiencia en pesos (COP)"),
    bigquery.SchemaField("experiencia_minima_contratos", "INT64", mode="NULLABLE", description="Numero minimo de contratos exigidos"),
    bigquery.SchemaField("financiero_liquidez", "STRING", mode="NULLABLE", description="Indicador de liquidez exigido (ej: >1.5)"),
    bigquery.SchemaField("financiero_endeudamiento", "STRING", mode="NULLABLE", description="Indicador de endeudamiento exigido (ej: <0.7)"),
    bigquery.SchemaField("personal_requerido", "STRING", mode="REPEATED", description="Perfiles de personal clave exigidos en pliegos"),
    bigquery.SchemaField("ultima_actualizacion", "TIMESTAMP", mode="REQUIRED", description="Fecha y hora de extraccion"),
]

table = bigquery.Table(table_id, schema=schema)

try:
    # Delete the table if it already exists to ensure a clean schema creation
    client.delete_table(table_id, not_found_ok=True)
    print(f"Table {table_id} deleted (if it existed).")
    
    # Create the table
    created_table = client.create_table(table)
    print(f"Created table {created_table.project}.{created_table.dataset_id}.{created_table.table_id} successfully.")
except Exception as e:
    print(f"Error creating table: {e}")
