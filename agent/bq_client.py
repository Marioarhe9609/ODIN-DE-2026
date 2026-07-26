"""Odin v2 - Shared BigQuery client and query helpers."""
import os
import google.auth
from google.auth.transport.requests import AuthorizedSession



from google.cloud import bigquery
import unicodedata
import contextvars
import re

# Initialize context variable for tracking generated excel files in the current async task context
generated_excels_var = contextvars.ContextVar("generated_excels_var", default=None)

PROJECT = os.getenv("GCP_PROJECT_ID", "proy-anla-poc")
DATASET = os.getenv("BQ_DATASET", "secop")

def _make_no_keepalive_session(credentials):
    """Build an AuthorizedSession that forces Connection: close and disables pool reuse,
    preventing stale keep-alive TLS socket errors on Cloud Run."""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = AuthorizedSession(credentials)
    session.headers.update({"Connection": "close"})
    
    adapter = HTTPAdapter(
        pool_connections=0,
        pool_maxsize=0,
        max_retries=Retry(total=3, backoff_factor=0.2, raise_on_status=False)
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_client():
    """Return resilient BigQuery client with no-keep-alive HTTP session."""
    try:
        import subprocess
        from google.oauth2.credentials import Credentials
        cmd = ["gcloud.cmd", "auth", "print-access-token"] if os.name == 'nt' else ["gcloud", "auth", "print-access-token"]
        token = subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout.strip()
        if token and len(token) > 20:
            credentials = Credentials(token)
            http = _make_no_keepalive_session(credentials)
            return bigquery.Client(project=PROJECT, credentials=credentials, _http=http)
    except Exception:
        pass

    # On Cloud Run: use Workload Identity with Connection: close session
    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        http = _make_no_keepalive_session(credentials)
        return bigquery.Client(project=PROJECT, credentials=credentials, _http=http)
    except Exception:
        pass

    return bigquery.Client(project=PROJECT)

class _ClientProxy:
    """Dynamic proxy that delegates every call to a fresh get_client() instance,
    guaranteeing no stale socket retention across requests on Cloud Run."""
    def __getattr__(self, name):
        fresh_client = get_client()
        return getattr(fresh_client, name)

client = _ClientProxy()

# Placeholder provider names to always exclude from results
JUNK_PROVIDERS = (
    'Sin Descripcion', 'SinDescripcion', 'SINDESCA', 'Sin descripción',
    'No Definido', 'No aplica', 'NO APLICA', 'NINGUNO',
    'N/A', 'n/a', 'NA', '.', '-', '0'
)
JUNK_FILTER_SQL = "AND LOWER(proveedor_adjudicado) NOT IN ('sin descripcion', 'sindescripcion', 'sindesca', 'sin descripción', 'no definido', 'no aplica', 'ninguno', 'n/a', 'na', '.', '-', '0')"


# Colombian Entity Acronyms & Synonyms mapping for intelligent fuzzy matching
ENTITY_SYNONYMS = {
    'MINDEFENSA': ['MINISTERIO DE DEFENSA', 'DEFENSA NACIONAL', 'MINDEF', '899999003'],
    'MINDEF': ['MINISTERIO DE DEFENSA', 'DEFENSA NACIONAL', 'MINDEFENSA', '899999003'],
    'MINTIC': ['MINISTERIO DE TECNOLOGIAS DE LA INFORMACION', 'TECNOLOGIAS DE LA INFORMACION Y LAS COMUNICACIONES', '899999053'],
    'DPS': ['PROSPERIDAD SOCIAL', '900097800'],
    'UARIV': ['UNIDAD DE ATENCION Y REPARACION INTEGRAL', 'VICTIMAS', '900490473'],
    'VICTIMAS': ['UNIDAD DE ATENCION Y REPARACION INTEGRAL', 'UARIV', 'VICTIMAS', '900490473'],
    'UNIDAD PARA LAS VICTIMAS': ['UNIDAD DE ATENCION Y REPARACION INTEGRAL', 'UARIV', 'VICTIMAS', '900490473'],
    'UNIDAD DE VICTIMAS': ['UNIDAD DE ATENCION Y REPARACION INTEGRAL', 'UARIV', 'VICTIMAS', '900490473'],
    'SENA': ['SERVICIO NACIONAL DE APRENDIZAJE', '899999034'],
    'INPEC': ['INSTITUTO NACIONAL PENITENCIARIO', '800215546'],
    'FAC': ['FUERZA AEREA', 'FUERZA AÉREA'],
    'PONAL': ['POLICIA NACIONAL', 'POLICÍA NACIONAL'],
    'EJERCITO': ['EJERCITO NACIONAL', 'EJÉRCITO NACIONAL'],
    'ARMADA': ['ARMADA NACIONAL'],
    'DIAN': ['DIRECCION DE IMPUESTOS Y ADUANAS NACIONALES', '800197268'],
    'IGAC': ['INSTITUTO GEOGRAFICO AGUSTIN CODAZZI', '899999004'],
    'ICBF': ['INSTITUTO COLOMBIANO DE BIENESTAR FAMILIAR', '899999239'],
    'DNP': ['DEPARTAMENTO NACIONAL DE PLANEACION', '899999038'],
    'DANE': ['DEPARTAMENTO ADMINISTRATIVO NACIONAL DE ESTADISTICA', '899999054'],
    'AND': ['AGENCIA NACIONAL DE DEFENSA JURIDICA', '901144049'],
    'ANE': ['AGENCIA NACIONAL DEL ESPECTRO', '900334265'],
    'CRC': ['COMISION DE REGULACION DE COMUNICACIONES', '830002593'],
    'RTVC': ['RADIO TELEVISION NACIONAL DE COLOMBIA', '900002583'],
}


def strip_accents(text: str) -> str:
    """Remove accents/tildes from text for search matching."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


STOP_WORDS = {
    'de', 'del', 'la', 'las', 'los', 'el', 'para', 'por', 'y', 'a', 'en', 'con',
    'su', 'sus', 'al', 'lo', 'como', 'mas', 'pero', 'un', 'una', 'unos', 'unas',
    'especial', 'nacional', 'general', 'republica'
}


def safe_like(column: str, value: str) -> str:
    """Build an ultra-fast, robust SQL condition that matches ANY entity in Colombia.
    Automatically handles accents, stop-words, inserted terms (e.g. 'Unidad para las Víctimas'
    -> 'UARIV-UNIDAD PARA LA ATENCION Y REPARACION...'), acronyms, and fuzzy variations.
    """
    clean = strip_accents(value.lower()).strip()
    val_upper = strip_accents(value.upper()).strip()
    
    # 1. Check exact acronym match from ENTITY_SYNONYMS table
    synonym_terms = []
    for k, aliases in ENTITY_SYNONYMS.items():
        if k == val_upper:
            for alias in aliases:
                c_alias = strip_accents(alias.lower()).replace("'", "''")
                if c_alias not in synonym_terms:
                    synonym_terms.append(c_alias)
                    
    if synonym_terms:
        conds = [f"LOWER({column}) LIKE '%{t}%'" for t in synonym_terms]
        return f"({' OR '.join(conds)})"

    # 2. General keyword-based fuzzy matching for any Colombian entity
    words = re.findall(r'\b[a-z0-9]+\b', clean)
    sig_words = [w.replace("'", "''") for w in words if w not in STOP_WORDS and len(w) > 1]
    if not sig_words:
        sig_words = [w.replace("'", "''") for w in words] if words else [clean]
        
    word_conds = [f"LOWER({column}) LIKE '%{w}%'" for w in sig_words]
    return f"({' AND '.join(word_conds)})"

def query(sql: str, max_rows: int = 50, timeout_sec: float = 30) -> list[dict]:
    """Run a BigQuery SQL query and return results as list of dicts. Auto-reconnects on socket error."""
    global client
    try:
        job = client.query(sql)
        rows = list(job.result(max_results=max_rows, timeout=timeout_sec))
        return [dict(r) for r in rows]
    except Exception as e:
        # If connection was dropped by Cloud Run, recreate client and retry once
        err_str = str(e).lower()
        if "ssl" in err_str or "connection" in err_str or "eof" in err_str or "remote" in err_str:
            client = get_client()
            job = client.query(sql)
            rows = list(job.result(max_results=max_rows, timeout=timeout_sec))
            return [dict(r) for r in rows]
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
