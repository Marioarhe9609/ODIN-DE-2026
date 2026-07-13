"""
Odin v2 - Initial Load: SECOP II Procesos de Contratación
Ingests all SECOP II procurement processes from datos.gov.co into BigQuery.

Dataset: p6dx-8zbt (SECOP II - Procesos de Contratación)
API: SODA API (https://www.datos.gov.co/resource/p6dx-8zbt.json)
Target: BigQuery table odin-v2-495523.secop.procesos_contratacion
"""

import json
import hashlib
import time
import logging
import sys
from datetime import datetime, timezone

import requests
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# ─── Configuration ───────────────────────────────────────────────────────────
PROJECT_ID = "odin-v2-495523"
DATASET_ID = "secop"
TABLE_ID = "procesos_contratacion"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

SODA_API_BASE = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
BATCH_SIZE = 50000
REQUEST_DELAY = 0.5
MAX_RETRIES = 5

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("initial_load_procesos.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ─── Field Mapping ───────────────────────────────────────────────────────────
FIELD_MAP = {
    "descripci_n_del_procedimiento": "descripcion_del_procedimiento",
    "fecha_de_publicacion_del": "fecha_de_publicacion_del_proceso",
    "fecha_de_ultima_publicaci": "fecha_de_ultima_publicacion",
    "fecha_de_publicacion_fase": "fecha_publicacion_fase_planeacion_precalif",
    "fecha_de_publicacion_fase_1": "fecha_publicacion_fase_seleccion_precalif",
    "fecha_de_publicacion": "fecha_publicacion_manifestacion_interes",
    "fecha_de_publicacion_fase_2": "fecha_publicacion_fase_borrador",
    "fecha_de_publicacion_fase_3": "fecha_publicacion_fase_seleccion",
    "justificaci_n_modalidad_de": "justificacion_modalidad_de_contratacion",
    "unidad_de_duracion": "unidad_de_duracion",
    "ciudad_de_la_unidad_de": "ciudad_unidad_contratacion",
    "nombre_de_la_unidad_de": "nombre_unidad_contratacion",
    "proveedores_con_invitacion": "proveedores_con_invitacion_directa",
    "visualizaciones_del": "visualizaciones_del_procedimiento",
    "proveedores_que_manifestaron": "proveedores_que_manifestaron_interes",
    "conteo_de_respuestas_a_ofertas": "conteo_respuestas_ofertas",
    "proveedores_unicos_con": "proveedores_unicos_con_respuesta",
    "numero_de_lotes": "numero_de_lotes",
    "id_estado_del_procedimiento": "id_estado_del_procedimiento",
    "id_adjudicacion": "id_adjudicacion",
    "codigo_principal_de_categoria": "codigo_principal_de_categoria",
    "estado_de_apertura_del_proceso": "estado_de_apertura_del_proceso",
    "codigo_pci": "entidad_centralizada",
    "ordenentidad": "orden_entidad",
    "entidad": "nombre_entidad",
    "categorias_adicionales": "categorias_adicionales",
    "codigoproveedor": "codigo_proveedor",
    "estado_resumen": "estado_resumen",
}

TIMESTAMP_FIELDS = {
    "fecha_de_publicacion_del_proceso", "fecha_de_ultima_publicacion",
    "fecha_publicacion_fase_planeacion_precalif", "fecha_publicacion_fase_seleccion_precalif",
    "fecha_publicacion_manifestacion_interes", "fecha_publicacion_fase_borrador",
    "fecha_publicacion_fase_seleccion",
}

NUMERIC_FIELDS = {"precio_base", "valor_total_adjudicacion"}

INTEGER_FIELDS = {
    "duracion", "proveedores_invitados", "proveedores_con_invitacion_directa",
    "visualizaciones_del_procedimiento", "proveedores_que_manifestaron_interes",
    "respuestas_al_procedimiento", "respuestas_externas",
    "conteo_respuestas_ofertas", "proveedores_unicos_con_respuesta",
    "numero_de_lotes", "codigo_entidad",
}


def compute_hash(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def transform_record(raw: dict) -> dict:
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for api_key, value in raw.items():
        bq_key = FIELD_MAP.get(api_key, api_key)

        if bq_key == "urlproceso" and isinstance(value, dict):
            value = value.get("url", "")

        if bq_key.startswith(":"):
            continue

        record[bq_key] = value

    # Type conversions
    for field in TIMESTAMP_FIELDS:
        if field in record and record[field]:
            try:
                val = record[field]
                if isinstance(val, str) and val.strip():
                    record[field] = val
                else:
                    record[field] = None
            except Exception:
                record[field] = None

    for field in NUMERIC_FIELDS:
        if field in record:
            try:
                val = record[field]
                if val is not None and str(val).strip():
                    record[field] = float(str(val).replace(",", ""))
                else:
                    record[field] = None
            except (ValueError, TypeError):
                record[field] = None

    for field in INTEGER_FIELDS:
        if field in record:
            try:
                val = record[field]
                if val is not None and str(val).strip():
                    record[field] = int(float(str(val)))
                else:
                    record[field] = None
            except (ValueError, TypeError):
                record[field] = None

    record["_ingested_at"] = now
    record["_source_hash"] = compute_hash(raw)

    return record


def fetch_page(offset: int, limit: int = BATCH_SIZE) -> list:
    params = {"$limit": limit, "$offset": offset, "$order": ":id"}
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(SODA_API_BASE, params=params, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt
            logger.warning(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    logger.error(f"Failed to fetch offset {offset} after {MAX_RETRIES} retries")
    return []


def ensure_table(client: bigquery.Client):
    try:
        client.get_table(FULL_TABLE_ID)
        logger.info(f"Table {FULL_TABLE_ID} already exists")
        return
    except NotFound:
        pass

    schema = [
        # Entidad
        bigquery.SchemaField("nombre_entidad", "STRING"),
        bigquery.SchemaField("nit_entidad", "STRING"),
        bigquery.SchemaField("departamento_entidad", "STRING"),
        bigquery.SchemaField("ciudad_entidad", "STRING"),
        bigquery.SchemaField("orden_entidad", "STRING"),
        bigquery.SchemaField("entidad_centralizada", "STRING"),
        bigquery.SchemaField("codigo_entidad", "INT64"),
        bigquery.SchemaField("ppi", "STRING"),
        # Proceso
        bigquery.SchemaField("id_del_proceso", "STRING"),
        bigquery.SchemaField("referencia_del_proceso", "STRING"),
        bigquery.SchemaField("id_del_portafolio", "STRING"),
        bigquery.SchemaField("nombre_del_procedimiento", "STRING"),
        bigquery.SchemaField("descripcion_del_procedimiento", "STRING"),
        bigquery.SchemaField("fase", "STRING"),
        bigquery.SchemaField("estado_del_procedimiento", "STRING"),
        bigquery.SchemaField("id_estado_del_procedimiento", "STRING"),
        bigquery.SchemaField("estado_de_apertura_del_proceso", "STRING"),
        bigquery.SchemaField("estado_resumen", "STRING"),
        # Fechas
        bigquery.SchemaField("fecha_de_publicacion_del_proceso", "TIMESTAMP"),
        bigquery.SchemaField("fecha_de_ultima_publicacion", "TIMESTAMP"),
        bigquery.SchemaField("fecha_publicacion_fase_planeacion_precalif", "TIMESTAMP"),
        bigquery.SchemaField("fecha_publicacion_fase_seleccion_precalif", "TIMESTAMP"),
        bigquery.SchemaField("fecha_publicacion_manifestacion_interes", "TIMESTAMP"),
        bigquery.SchemaField("fecha_publicacion_fase_borrador", "TIMESTAMP"),
        bigquery.SchemaField("fecha_publicacion_fase_seleccion", "TIMESTAMP"),
        # Contratación
        bigquery.SchemaField("precio_base", "NUMERIC"),
        bigquery.SchemaField("modalidad_de_contratacion", "STRING"),
        bigquery.SchemaField("justificacion_modalidad_de_contratacion", "STRING"),
        bigquery.SchemaField("duracion", "INT64"),
        bigquery.SchemaField("unidad_de_duracion", "STRING"),
        bigquery.SchemaField("tipo_de_contrato", "STRING"),
        bigquery.SchemaField("subtipo_de_contrato", "STRING"),
        bigquery.SchemaField("codigo_principal_de_categoria", "STRING"),
        bigquery.SchemaField("categorias_adicionales", "STRING"),
        # Unidad de contratación
        bigquery.SchemaField("ciudad_unidad_contratacion", "STRING"),
        bigquery.SchemaField("nombre_unidad_contratacion", "STRING"),
        # Proveedores
        bigquery.SchemaField("proveedores_invitados", "INT64"),
        bigquery.SchemaField("proveedores_con_invitacion_directa", "INT64"),
        bigquery.SchemaField("visualizaciones_del_procedimiento", "INT64"),
        bigquery.SchemaField("proveedores_que_manifestaron_interes", "INT64"),
        bigquery.SchemaField("respuestas_al_procedimiento", "INT64"),
        bigquery.SchemaField("respuestas_externas", "INT64"),
        bigquery.SchemaField("conteo_respuestas_ofertas", "INT64"),
        bigquery.SchemaField("proveedores_unicos_con_respuesta", "INT64"),
        bigquery.SchemaField("numero_de_lotes", "INT64"),
        # Adjudicación
        bigquery.SchemaField("adjudicado", "STRING"),
        bigquery.SchemaField("id_adjudicacion", "STRING"),
        bigquery.SchemaField("codigo_proveedor", "STRING"),
        bigquery.SchemaField("departamento_proveedor", "STRING"),
        bigquery.SchemaField("ciudad_proveedor", "STRING"),
        bigquery.SchemaField("valor_total_adjudicacion", "NUMERIC"),
        bigquery.SchemaField("nombre_del_adjudicador", "STRING"),
        bigquery.SchemaField("nombre_del_proveedor", "STRING"),
        bigquery.SchemaField("nit_del_proveedor_adjudicado", "STRING"),
        # URL
        bigquery.SchemaField("urlproceso", "STRING"),
        # Metadata
        bigquery.SchemaField("_ingested_at", "TIMESTAMP"),
        bigquery.SchemaField("_source_hash", "STRING"),
    ]

    table = bigquery.Table(FULL_TABLE_ID, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.MONTH,
        field="fecha_de_publicacion_del_proceso"
    )
    table.clustering_fields = ["departamento_entidad", "nombre_entidad", "modalidad_de_contratacion"]
    table.description = "Procesos de contratación SECOP II - Datos Abiertos Colombia"

    client.create_table(table)
    logger.info(f"Table {FULL_TABLE_ID} created with partitioning and clustering")


def load_to_bigquery(client: bigquery.Client, records: list):
    if not records:
        return 0

    # Get current table schema to preserve existing types
    table = client.get_table(FULL_TABLE_ID)
    existing_fields = {f.name: f for f in table.schema}

    # Detect new fields from records that aren't in the schema
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())
    new_fields = all_keys - set(existing_fields.keys())

    # Build extended schema: existing fields + new ones as STRING
    extended_schema = list(table.schema)
    if new_fields:
        for field_name in sorted(new_fields):
            extended_schema.append(bigquery.SchemaField(field_name, "STRING"))
            logger.info(f"  📌 New field detected, adding as STRING: {field_name}")

    # Convert all values for known STRING fields to str to avoid type conflicts
    string_fields = {f.name for f in extended_schema if f.field_type == "STRING"}
    for r in records:
        for key in list(r.keys()):
            if key in string_fields and r[key] is not None:
                r[key] = str(r[key])

    job_config = bigquery.LoadJobConfig(
        schema=extended_schema,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ignore_unknown_values=True,
    )
    job = client.load_table_from_json(records, FULL_TABLE_ID, job_config=job_config)
    job.result()
    return len(records)


def get_current_count(client: bigquery.Client) -> int:
    try:
        query = f"SELECT COUNT(*) as cnt FROM `{FULL_TABLE_ID}`"
        result = list(client.query(query).result())
        return result[0].cnt
    except Exception:
        return 0


def main():
    logger.info("=" * 60)
    logger.info("Odin v2 - SECOP II Procesos de Contratación - Initial Load")
    logger.info("=" * 60)

    client = bigquery.Client(project=PROJECT_ID)

    # Ensure table exists (dataset should exist from contratos load)
    ensure_table(client)

    # Resume logic
    current_count = get_current_count(client)
    start_offset = current_count
    if current_count > 0:
        logger.info(f"Resuming from offset {current_count} (existing rows in BQ)")
    else:
        logger.info("Starting fresh load from offset 0")

    # Get total count
    try:
        resp = requests.get(f"{SODA_API_BASE}?$select=count(*)", timeout=30)
        total = int(resp.json()[0]["count"])
        logger.info(f"Total records in SECOP II Procesos API: {total:,}")
    except Exception as e:
        logger.warning(f"Could not get total count: {e}. Using estimate.")
        total = 8_700_000

    # Fetch and load
    offset = start_offset
    total_loaded = 0
    batch_num = 0
    start_time = time.time()

    while offset < total:
        batch_num += 1
        logger.info(f"[Batch {batch_num}] Fetching offset {offset:,} / {total:,} ({offset/total*100:.1f}%)")

        raw_records = fetch_page(offset, BATCH_SIZE)
        if not raw_records:
            logger.info("No more records. Finished.")
            break

        transformed = []
        for raw in raw_records:
            try:
                transformed.append(transform_record(raw))
            except Exception as e:
                logger.warning(f"Failed to transform record: {e}")
                continue

        try:
            loaded = load_to_bigquery(client, transformed)
            total_loaded += loaded
            elapsed = time.time() - start_time
            rate = total_loaded / elapsed if elapsed > 0 else 0
            remaining = (total - offset - len(raw_records)) / rate if rate > 0 else 0

            logger.info(
                f"[Batch {batch_num}] Loaded {loaded:,} rows | "
                f"Total: {total_loaded:,} | "
                f"Rate: {rate:,.0f} rows/sec | "
                f"ETA: {remaining/60:.1f} min"
            )
        except Exception as e:
            logger.error(f"[Batch {batch_num}] BigQuery load failed: {e}")
            logger.info("Saving checkpoint. You can resume by re-running this script.")
            break

        offset += len(raw_records)
        time.sleep(REQUEST_DELAY)

    # Final summary
    elapsed_total = time.time() - start_time
    final_count = get_current_count(client)

    logger.info("=" * 60)
    logger.info("LOAD COMPLETE")
    logger.info(f"Total rows in BigQuery: {final_count:,}")
    logger.info(f"Rows loaded this run: {total_loaded:,}")
    logger.info(f"Total time: {elapsed_total/60:.1f} minutes")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
