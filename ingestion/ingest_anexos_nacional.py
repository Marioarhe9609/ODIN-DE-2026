"""
Odin v2 / ANLA PoC - Focused Ingestion Pipeline for SECOP II Document Annexes (dmgg-8hin)
STRICT TARGETING:
1. Sector Defensa (MinDefensa 899999003, Agencia Logística 899999162, HospMilitar 830040256, INDUMIL 899999044, CREMIL 860021967, Caja Honor 860021180, Defensa Civil 860021653, FORPO 860020227, SuperVigilancia 800217123)
2. Sector TIC (MinTIC 899999053, ANE 900334265, CRC 830002593, AND 901144049, FUTIC 8001316486, RTVC 900002583, 4-72 900062917, CPE 830079479)
3. Sector Inclusión Social y Reconciliación (DPS 900097800, UARIV 900490473, CNMH 900492970)

Extracts structured audit data with Gemini 2.5 Flash, generates 768-dim embeddings with Vertex AI text-embedding-004,
and stores in BigQuery (proy-anla-poc.secop).
"""
import os
import re
import uuid
import json
import time
import requests
import datetime
import subprocess
import random
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types as genai_types
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

PROJECT = os.getenv("GCP_PROJECT_ID", "proy-anla-poc")
DATASET = os.getenv("BQ_DATASET", "secop")

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# Local credential fallback only if file exists
local_adc = r"C:\Users\ASUS\AppData\Roaming\gcloud\legacy_credentials\marioarevaloh@gmail.com\adc.json"
if os.path.exists(local_adc) and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_adc


def get_bq_client():
    """Return BigQuery client compatible with both Cloud Run ADC and local gcloud tokens."""
    try:
        return bigquery.Client(project=PROJECT)
    except Exception:
        pass
        
    try:
        cmd = ["gcloud.cmd", "auth", "print-access-token"] if os.name == 'nt' else ["gcloud", "auth", "print-access-token"]
        token = subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout.strip()
        if token:
            credentials = Credentials(token)
            return bigquery.Client(project=PROJECT, credentials=credentials)
    except Exception:
        pass
        
    return bigquery.Client(project=PROJECT)


# AI Client
ai_client = genai.Client(vertexai=True, project=PROJECT, location="us-central1")


# STRICT TARGET NITS & KEYWORDS FOR THE 3 SECTORS
TARGET_SECTOR_NITS = {
    # 1. Sector Defensa
    "899999003", # MinDefensa, FONDETEC, Ejército, Armada, Fuerza Aeroespacial, Comando General, DIMAR
    "899999162", # Agencia Logística de las Fuerzas Militares
    "830040256", # Hospital Militar Central
    "899999044", # Industria Militar (INDUMIL)
    "860021967", # CREMIL
    "860021180", # Caja Honor
    "860021653", # Defensa Civil Colombiana
    "860020227", # FORPO (Fondo Rotatorio de la Policía)
    "800217123", # Superintendencia de Vigilancia y Seguridad Privada
    # 2. Sector TIC
    "899999053", # MinTIC
    "900334265", # ANE (Agencia Nacional del Espectro)
    "830002593", # CRC (Comisión de Regulación de Comunicaciones)
    "901144049", # AND (Agencia Nacional Digital)
    "8001316486",# FUTIC
    "800131648",
    "900002583", # RTVC (Sistema de Medios Públicos / Inravisión)
    "900062917", # 4-72 (Servicios Postales Nacionales)
    "830079479", # CPE (Computadores para Educar)
    # 3. Sector Inclusión Social y Reconciliación
    "900097800", # DPS (Prosperidad Social)
    "900490473", # UARIV (Unidad para las Víctimas)
    "900492970"  # CNMH (Centro Nacional de Memoria Histórica)
}

TARGET_SECTOR_KEYWORDS = [
    # Defensa
    "MINISTERIO DE DEFENSA", "ARMADA NACIONAL", "FUERZA AEREA", "FUERZA AEROESPACIAL", 
    "EJERCITO NACIONAL", "COMANDO GENERAL DE LAS FUERZAS MILITARES", "DIMAR", 
    "DIRECCION GENERAL MARITIMA", "AGENCIA LOGISTICA DE LAS FUERZAS MILITARES", 
    "HOSPITAL MILITAR CENTRAL", "INDUMIL", "INDUSTRIA MILITAR", "CREMIL", 
    "CAJA HONOR", "CAJA PROMOTORA DE VIVIENDA MILITAR", "DEFENSA CIVIL COLOMBIANA", 
    "FORPO", "FONDO ROTATORIO DE LA POLICIA", "SUPERINTENDENCIA DE VIGILANCIA",
    # TIC
    "MINISTERIO DE TECNOLOGIAS DE LA INFORMACION", "MINTIC", "AGENCIA NACIONAL DEL ESPECTRO", 
    "COMISION DE REGULACION DE COMUNICACIONES", "AGENCIA NACIONAL DIGITAL", "FUTIC", 
    "RTVC", "INRAVISION", "SERVICIOS POSTALES NACIONALES", "4-72", "COMPUTADORES PARA EDUCAR",
    # Inclusión Social
    "PROSPERIDAD SOCIAL", "DEPARTAMENTO ADMINISTRATIVO PARA LA PROSPERIDAD SOCIAL", "DPS",
    "UNIDAD PARA LA ATENCION Y REPARACION INTEGRAL A LAS VICTIMAS", "UARIV", "FONDO PARA LA REPARACION DE LAS VICTIMAS",
    "CENTRO NACIONAL DE MEMORIA HISTORICA", "CNMH"
]


def clean_nit(nit_str):
    if not nit_str:
        return ""
    return re.sub(r'\D', '', str(nit_str))


def fetch_national_documents(national_nits=None, limit=200):
    """Fetch PDFs strictly for Sector Defensa, Sector TIC, and Sector Inclusión Social."""
    url = "https://www.datos.gov.co/resource/dmgg-8hin.json"
    
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))
    task_partition_offset = (task_index * 1000) + (random.randint(0, 50) * 50)
    
    params = {
        "$where": "extensi_n = 'pdf' AND fecha_carga >= '2024-01-01T00:00:00'",
        "$limit": limit,
        "$offset": task_partition_offset,
        "$order": "fecha_carga DESC"
    }
    
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                records = resp.json()
                filtered = []
                for r in records:
                    nit_raw = r.get("nit_entidad", "")
                    nit_clean = clean_nit(nit_raw)
                    entidad = r.get("entidad", "").upper()
                    
                    is_nit_match = any(nit_clean.startswith(tn) for tn in TARGET_SECTOR_NITS)
                    is_keyword_match = any(k in entidad for k in TARGET_SECTOR_KEYWORDS)
                    
                    if is_nit_match or is_keyword_match:
                        filtered.append(r)
                return filtered
        except Exception as e:
            print(f"  [WARN SODA API] Intento {attempt+1}/3 falló ({e}), reintentando...", flush=True)
            time.sleep(2)
            
    return []


def download_pdf_text(doc_url):
    """Download PDF and extract text using PyPDF with strict size and page caps to prevent heavy token usage."""
    try:
        r = requests.get(doc_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) < 500:
            return None
        
        # 1. Try fast local PyPDF extraction (up to 8 pages)
        try:
            import pypdf
            reader = pypdf.PdfReader(BytesIO(r.content))
            text = ""
            for page in reader.pages[:8]:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            if len(text.strip()) > 80:
                return text[:10000]
        except Exception:
            pass

        # 2. Fallback to Gemini 2.5 Flash ONLY for small PDFs (< 2MB)
        if len(r.content) <= 2 * 1024 * 1024:
            pdf_part = genai_types.Part.from_bytes(data=r.content, mime_type="application/pdf")
            res = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[pdf_part, "Extrae el texto principal de este PDF de contratación pública."]
            )
            return res.text[:10000] if res and res.text else None
        else:
            return None
    except Exception:
        return None


def extract_audit_metadata(text, doc_meta):
    """Extract firmantes and entregables audit info with Gemini 2.5 Flash."""
    prompt = f"""
Analiza este documento contractual (Entidad: {doc_meta.get('entidad')}, Archivo: {doc_meta.get('nombre_archivo')}).
Texto:
\"\"\"
{text[:12000]}
\"\"\"

Extrae la siguiente información estructurada en formato JSON:
{{
  "firmantes": [
    {{"rol": "ESTRUCTURADOR | ORDENADOR | SUPERVISOR | REPR_LEGAL", "nombre": "Nombre completo", "numero_documento": "Cédula o NIT", "cargo": "Cargo", "entidad_o_empresa": "Entidad o Empresa"}}
  ],
  "entregables_auditoria": [
    {{"entregable_prometido": "Requisito contractual", "entregable_recibido": "Lo efectivamente recibido", "estado": "CUMPLIDO | INCUMPLIDO | PARCIAL", "alerta_aceptado_sin_implementar": false}}
  ]
}}
Devuelve únicamente JSON.
"""
    try:
        res = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        clean = re.sub(r'```json\s*|\s*```', '', res.text.strip())
        return json.loads(clean)
    except Exception:
        return None


def generate_embedding(text):
    """Generate 768-dimensional vector embedding with Vertex AI text-embedding-004."""
    try:
        res = ai_client.models.embed_content(
            model="text-embedding-004",
            contents=text[:2000]
        )
        return res.embeddings[0].values
    except Exception:
        return None


def process_single_document(doc):
    """Process a single document concurrently in a worker thread."""
    bq_client = get_bq_client()
    doc_id = doc.get("id_documento", str(uuid.uuid4().hex[:8]))
    proceso_id = doc.get("proceso", "")
    entidad = doc.get("entidad", "Entidad Sector Objetivo")
    nit_entidad = doc.get("nit_entidad", "")
    nombre_archivo = doc.get("nombre_archivo", "documento.pdf")
    url_raw = doc.get("url_descarga_documento", {})
    url_descarga = url_raw.get("url") if isinstance(url_raw, dict) else str(url_raw)
    
    # Check if already processed
    check_sql = f"SELECT id_documento FROM `{PROJECT}.{DATASET}.documentos_embeddings` WHERE id_documento = '{doc_id}' LIMIT 1"
    try:
        if list(bq_client.query(check_sql).result()):
            return f"SKIP {doc_id}"
    except Exception:
        pass
        
    text = download_pdf_text(url_descarga)
    if not text or len(text.strip()) < 50:
        return f"EMPTY {doc_id}"
        
    # 1. Audit Metadata
    audit_info = extract_audit_metadata(text, doc)
    if audit_info:
        for f in audit_info.get("firmantes", []):
            if f.get("nombre"):
                row = {
                    "id_contrato": proceso_id,
                    "rol": f.get("rol", "FIRMANTE"),
                    "nombre": f.get("nombre"),
                    "numero_documento": f.get("numero_documento", ""),
                    "cargo": f.get("cargo", ""),
                    "entidad_o_empresa": f.get("entidad_o_empresa", entidad)
                }
                bq_client.insert_rows_json(f"{PROJECT}.{DATASET}.contratos_firmantes_extendido", [row])
                
        for e in audit_info.get("entregables_auditoria", []):
            row = {
                "id_contrato": proceso_id,
                "entregable_prometido": e.get("entregable_prometido", ""),
                "entregable_recibido": e.get("entregable_recibido", ""),
                "estado": e.get("estado", "CUMPLIDO"),
                "evidencia_encontrada": nombre_archivo,
                "alerta_aceptado_sin_implementar": e.get("alerta_aceptado_sin_implementar", False)
            }
            bq_client.insert_rows_json(f"{PROJECT}.{DATASET}.contratos_auditoria_entregables", [row])

    # 2. Chunks and Vectors
    chunks = [text[i:i+800] for i in range(0, len(text), 800)][:4]
    inserted_vecs = 0
    for c_idx, chunk_text in enumerate(chunks):
        embedding_vec = generate_embedding(chunk_text)
        if embedding_vec:
            chunk_id = f"chunk_{doc_id}_{c_idx}_{uuid.uuid4().hex[:4]}"
            vec_row = {
                "id_chunk": chunk_id,
                "id_documento": doc_id,
                "id_contrato": proceso_id,
                "id_proceso": proceso_id,
                "nombre_entidad": entidad,
                "nit_entidad": nit_entidad,
                "orden_entidad": "Nacional - Sector Objetivo",
                "tipo_documento": "Documento Anexo SECOP II",
                "nombre_archivo": nombre_archivo,
                "url_archivo": url_descarga,
                "chunk_index": c_idx,
                "texto_chunk": chunk_text[:500],
                "embedding": embedding_vec,
                "fecha_creacion_doc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "fecha_carga": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            errs = bq_client.insert_rows_json(f"{PROJECT}.{DATASET}.documentos_embeddings", [vec_row])
            if not errs:
                inserted_vecs += 1
                
    print(f"  [OK HILO] Doc {doc_id} ({nombre_archivo[:30]}): {inserted_vecs} vectores insertados.", flush=True)
    return f"OK {doc_id}"


def run(max_documents=200, max_workers=5):
    task_idx = os.getenv("CLOUD_RUN_TASK_INDEX", "0")
    print(f"=== INICIANDO PIPELINE DE INGESTA DOCUMENTAL ENFOCADO EN 3 SECTORES (TAREA #{task_idx} - {max_workers} HILOS) ===", flush=True)
    
    docs = fetch_national_documents(limit=max_documents*3)
    print(f"Filtrados {len(docs)} documentos pertenecientes a Defensa, TIC e Inclusión Social.", flush=True)
    
    processed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_document, doc): doc for doc in docs[:max_documents]}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res and res.startswith("OK"):
                    processed_count += 1
            except Exception as e:
                print(f"  [ERR] Excepción en hilo: {e}", flush=True)
                
    print(f"\n=== PIPELINE SECTORES OBJETIVO COMPLETADO (TAREA #{task_idx}): {processed_count} documentos procesados ===", flush=True)

if __name__ == "__main__":
    max_docs = int(os.getenv("MAX_DOCUMENTS", "200"))
    max_workers = int(os.getenv("MAX_WORKERS", "5"))
    run(max_documents=max_docs, max_workers=max_workers)
