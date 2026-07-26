"""Odin v2 - Shared BigQuery client and query helpers."""
from google.cloud import bigquery
import os
import unicodedata
import contextvars

# Initialize context variable for tracking generated excel files in the current async task context
generated_excels_var = contextvars.ContextVar("generated_excels_var", default=None)

PROJECT = os.getenv("GCP_PROJECT_ID", "proy-anla-poc")
DATASET = os.getenv("BQ_DATASET", "secop")
client = bigquery.Client(project=PROJECT)

# Placeholder provider names to always exclude from results
JUNK_PROVIDERS = (
    'Sin Descripcion', 'SinDescripcion', 'SINDESCA', 'Sin descripción',
    'No Definido', 'No aplica', 'NO APLICA', 'NINGUNO',
    'N/A', 'n/a', 'NA', '.', '-', '0'
)
JUNK_FILTER_SQL = "AND LOWER(proveedor_adjudicado) NOT IN ('sin descripcion', 'sindescripcion', 'sindesca', 'sin descripción', 'no definido', 'no aplica', 'ninguno', 'n/a', 'na', '.', '-', '0')"


def strip_accents(text: str) -> str:
    """Remove accents/tildes from text for search matching."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def safe_like(column: str, value: str) -> str:
    """Build a LIKE clause that works regardless of accents/tildes.
    Uses BigQuery NORMALIZE + REGEXP_REPLACE to strip diacritics on both sides."""
    clean = strip_accents(value.lower()).replace("'", "''")
    return (f"LOWER(REGEXP_REPLACE(NORMALIZE({column}, NFD), r'\\pM', '')) "
            f"LIKE '%{clean}%'")

def query(sql: str, max_rows: int = 50, timeout_sec: float = 30) -> list[dict]:
    """Run a BigQuery SQL query and return results as list of dicts."""
    job = client.query(sql)
    try:
        rows = list(job.result(max_results=max_rows, timeout=timeout_sec))
        return [dict(r) for r in rows]
    except Exception as e:
        # Cancel the job if it's still running
        try:
            job.cancel()
        except Exception:
            pass
        raise e

def query_view(view_name: str, where: str = "", order: str = "", limit: int = 20, timeout_sec: float = 30) -> list[dict]:
    """Query an analytical view with optional filters."""
    sql = f"SELECT * FROM `{PROJECT}.{DATASET}.{view_name}`"
    if where:
        sql += f" WHERE {where}"
    if order:
        sql += f" ORDER BY {order}"
    sql += f" LIMIT {limit}"
    return query(sql, max_rows=limit, timeout_sec=timeout_sec)

def format_table(rows: list[dict], max_cols: int = 15) -> str:
    """Format query results as a readable text table with clickable markdown links for URLs."""
    if not rows:
        return "Sin resultados."
    keys = list(rows[0].keys())[:max_cols]
    def fmt(k, v):
        s = str(v) if v is not None else "-"
        if k.lower() in ('url', 'urlproceso', 'url_archivo', 'url_proceso', 'archivo_anexo', 'url_descarga'):
            return s
        return s[:120] + "..." if len(s) > 120 else s
        
    lines = []
    for i, r in enumerate(rows, 1):
        lines.append(f"📋 **Registro #{i}**")
        for k in keys:
            val = fmt(k, r.get(k))
            key_clean = k.replace('_', ' ').title()
            
            # Format URLs as clickable markdown links
            if k.lower() in ('url_archivo', 'url_descarga') and str(val).startswith('http'):
                lines.append(f"  • 📄 **{key_clean}:** [{r.get('nombre_archivo', 'Ver PDF Anexo Original')}]({val})")
            elif k.lower() in ('url', 'urlproceso', 'url_proceso') and str(val).startswith('http'):
                lines.append(f"  • 🔗 **{key_clean}:** [Ver Proceso en SECOP II]({val})")
            else:
                lines.append(f"  • **{key_clean}:** {val}")
        lines.append("")  # Empty line separator
        
    table_text = "\n".join(lines).strip()

    # Generate temporary Excel file for potential export
    try:
        import pandas as pd
        import uuid
        import os
        import logging
        os.makedirs("temp_downloads", exist_ok=True)
        # Create DataFrame and save
        df = pd.DataFrame(rows)
        # Clean URLs if they are dictionaries
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, dict)).any():
                df[col] = df[col].apply(lambda x: x.get('url', '') if isinstance(x, dict) else x)
                
            # Excel does not support datetimes with timezones
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = df[col].dt.tz_localize(None)
                except Exception:
                    pass
                
        filename = f"datos_{uuid.uuid4().hex[:8]}.xlsx"
        filepath = os.path.join("temp_downloads", filename)
        df.to_excel(filepath, index=False)
        table_text += f"\n[EXCEL:{filename}]\n"
        
        # Track the generated Excel filepath in our ContextVar
        lst = generated_excels_var.get()
        if lst is not None:
            lst.append(os.path.abspath(filepath))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error generating Excel in bq_client: {e}")

    return table_text
