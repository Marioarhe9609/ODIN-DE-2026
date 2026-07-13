"""Odin v2 - Memory and Auto-Adjustment tools."""
import uuid
from datetime import datetime
from google.cloud import bigquery
from agent.bq_client import PROJECT, DATASET

def aprender_regla(regla_texto: str) -> str:
    """Guarda una nueva regla de negocio o correccion en la memoria a largo plazo de Odin.
    Esta regla se leera automaticamente en cada conversacion futura para evitar cometer el mismo error.
    Args:
        regla_texto: La instruccion o correccion (ej. "Las uniones temporales no son colusion si no ganan contratos").
    """
    client = bigquery.Client(project=PROJECT)
    table_id = f"{PROJECT}.{DATASET}.memoria_odin"
    
    regla_id = str(uuid.uuid4())[:8]
    now_str = datetime.utcnow().isoformat()
    
    rows_to_insert = [
        {"id": regla_id, "regla": regla_texto, "fecha_creacion": now_str}
    ]
    
    errors = client.insert_rows_json(table_id, rows_to_insert)
    if not errors:
        return f"✅ Regla guardada exitosamente en la memoria a largo plazo con ID {regla_id}. Odin no olvidara esto."
    else:
        return f"Error al guardar la regla: {errors}"

TOOLS = [aprender_regla]
