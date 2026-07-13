"""
Odin v2 - Initial Load Script
Ingests all SECOP II electronic contracts from datos.gov.co into BigQuery.

Dataset: jbjy-vk9h (SECOP II - Contratos Electrónicos)
API: SODA API (https://www.datos.gov.co/resource/jbjy-vk9h.json)
Target: BigQuery table odin-v2-495523.secop.contratos_electronicos
"""

import json
import hashlib
import time
import logging
import sys
import os
from datetime import datetime, timezone

import requests
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# ─── Configuration ───────────────────────────────────────────────────────────
PROJECT_ID = "odin-v2-495523"
DATASET_ID = "secop"
TABLE_ID = "contratos_electronicos"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

SODA_API_BASE = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
BATCH_SIZE = 50000        # Max rows per SODA API request
BQ_INSERT_BATCH = 10000   # Rows per BigQuery streaming insert
REQUEST_DELAY = 0.5       # Seconds between API requests
MAX_RETRIES = 5           # Max retries per failed request

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("initial_load.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ─── Field Mapping ───────────────────────────────────────────────────────────
# Maps SODA API field names to BigQuery column names (for fields with different names)
FIELD_MAP = {
    "localizaci_n": "localizacion",
    "liquidaci_n": "liquidacion",
    "obligaci_n_ambiental": "obligacion_ambiental",
    "valor_pendiente_de": "valor_pendiente_de_amortizacion",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_": "recursos_propios_territorial",
    "tipo_de_identificaci_n_representante_legal": "tipo_identificacion_representante_legal",
    "identificaci_n_representante_legal": "identificacion_representante_legal",
    "g_nero_representante_legal": "genero_representante_legal",
    "n_mero_de_documento_ordenador_del_gasto": "numero_documento_ordenador_del_gasto",
    "tipo_de_documento_ordenador_del_gasto": "tipo_documento_ordenador_del_gasto",
    "n_mero_de_documento_supervisor": "numero_documento_supervisor",
    "tipo_de_documento_supervisor": "tipo_documento_supervisor",
    "n_mero_de_documento_ordenador_de_pago": "numero_documento_ordenador_de_pago",
    "tipo_de_documento_ordenador_de_pago": "tipo_documento_ordenador_de_pago",
    "duraci_n_del_contrato": "duracion_del_contrato",
    "n_mero_de_cuenta": "numero_de_cuenta",
    "fecha_de_notificaci_n_de_prorrogaci_n": "fecha_de_notificacion_de_prorrogacion",
    "sistema_general_de_regal_as": "sistema_general_de_regalias",
}

TIMESTAMP_FIELDS = {
    "fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato",
    "fecha_inicio_liquidacion", "fecha_fin_liquidacion", "ultima_actualizacion",
    "fecha_de_notificacion_de_prorrogacion"
}

NUMERIC_FIELDS = {
    "valor_del_contrato", "valor_de_pago_adelantado", "valor_facturado",
    "valor_pendiente_de_pago", "valor_pagado", "valor_amortizado",
    "valor_pendiente_de_amortizacion", "valor_pendiente_de_ejecucion",
    "saldo_cdp", "saldo_vigencia", "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regalias",
    "recursos_propios_territorial", "recursos_de_credito", "recursos_propios"
}

INTEGER_FIELDS = {"codigo_entidad", "dias_adicionados"}


def compute_hash(record: dict) -> str:
    """Compute a deterministic hash for deduplication."""
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def transform_record(raw: dict) -> dict:
    """Transform a SODA API record to BigQuery schema."""
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for api_key, value in raw.items():
        # Map field name
        bq_key = FIELD_MAP.get(api_key, api_key)

        # Handle URL object fields
        if bq_key == "urlproceso" and isinstance(value, dict):
            value = value.get("url", "")

        # Skip unknown fields
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

    # NIT as string
    if "nit_entidad" in record:
        record["nit_entidad"] = str(record["nit_entidad"]) if record["nit_entidad"] else None

    # Add metadata
    record["_ingested_at"] = now
    record["_source_hash"] = compute_hash(raw)

    return record


def fetch_page(offset: int, limit: int = BATCH_SIZE) -> list:
    """Fetch a page of records from the SODA API with retry logic."""
    params = {
        "$limit": limit,
        "$offset": offset,
        "$order": ":id"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(SODA_API_BASE, params=params, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt
            logger.warning(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
            time.sleep(wait)

    logger.error(f"Failed to fetch offset {offset} after {MAX_RETRIES} retries")
    return []


def ensure_dataset(client: bigquery.Client):
    """Create the BigQuery dataset if it doesn't exist."""
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = "US"
    dataset_ref.description = "SECOP II - Datos de contratación pública colombiana"

    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {DATASET_ID} already exists")
    except NotFound:
        client.create_dataset(dataset_ref)
        logger.info(f"Dataset {DATASET_ID} created")


def ensure_table(client: bigquery.Client):
    """Create the BigQuery table if it doesn't exist, using schema.sql logic."""
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
        bigquery.SchemaField("departamento", "STRING"),
        bigquery.SchemaField("ciudad", "STRING"),
        bigquery.SchemaField("localizacion", "STRING"),
        bigquery.SchemaField("orden", "STRING"),
        bigquery.SchemaField("sector", "STRING"),
        bigquery.SchemaField("rama", "STRING"),
        bigquery.SchemaField("entidad_centralizada", "STRING"),
        bigquery.SchemaField("codigo_entidad", "INT64"),
        # Contrato
        bigquery.SchemaField("proceso_de_compra", "STRING"),
        bigquery.SchemaField("id_contrato", "STRING"),
        bigquery.SchemaField("referencia_del_contrato", "STRING"),
        bigquery.SchemaField("estado_contrato", "STRING"),
        bigquery.SchemaField("codigo_de_categoria_principal", "STRING"),
        bigquery.SchemaField("descripcion_del_proceso", "STRING"),
        bigquery.SchemaField("objeto_del_contrato", "STRING"),
        bigquery.SchemaField("tipo_de_contrato", "STRING"),
        bigquery.SchemaField("modalidad_de_contratacion", "STRING"),
        bigquery.SchemaField("justificacion_modalidad_de", "STRING"),
        bigquery.SchemaField("condiciones_de_entrega", "STRING"),
        bigquery.SchemaField("duracion_del_contrato", "STRING"),
        # Fechas
        bigquery.SchemaField("fecha_de_firma", "TIMESTAMP"),
        bigquery.SchemaField("fecha_de_inicio_del_contrato", "TIMESTAMP"),
        bigquery.SchemaField("fecha_de_fin_del_contrato", "TIMESTAMP"),
        bigquery.SchemaField("fecha_inicio_liquidacion", "TIMESTAMP"),
        bigquery.SchemaField("fecha_fin_liquidacion", "TIMESTAMP"),
        bigquery.SchemaField("ultima_actualizacion", "TIMESTAMP"),
        bigquery.SchemaField("fecha_de_notificacion_de_prorrogacion", "TIMESTAMP"),
        # Proveedor
        bigquery.SchemaField("tipodocproveedor", "STRING"),
        bigquery.SchemaField("documento_proveedor", "STRING"),
        bigquery.SchemaField("proveedor_adjudicado", "STRING"),
        bigquery.SchemaField("codigo_proveedor", "STRING"),
        bigquery.SchemaField("es_grupo", "STRING"),
        bigquery.SchemaField("es_pyme", "STRING"),
        # Valores
        bigquery.SchemaField("valor_del_contrato", "NUMERIC"),
        bigquery.SchemaField("valor_de_pago_adelantado", "NUMERIC"),
        bigquery.SchemaField("valor_facturado", "NUMERIC"),
        bigquery.SchemaField("valor_pendiente_de_pago", "NUMERIC"),
        bigquery.SchemaField("valor_pagado", "NUMERIC"),
        bigquery.SchemaField("valor_amortizado", "NUMERIC"),
        bigquery.SchemaField("valor_pendiente_de_amortizacion", "NUMERIC"),
        bigquery.SchemaField("valor_pendiente_de_ejecucion", "NUMERIC"),
        bigquery.SchemaField("saldo_cdp", "NUMERIC"),
        bigquery.SchemaField("saldo_vigencia", "NUMERIC"),
        # Origen recursos
        bigquery.SchemaField("origen_de_los_recursos", "STRING"),
        bigquery.SchemaField("destino_gasto", "STRING"),
        bigquery.SchemaField("presupuesto_general_de_la_nacion_pgn", "NUMERIC"),
        bigquery.SchemaField("sistema_general_de_participaciones", "NUMERIC"),
        bigquery.SchemaField("sistema_general_de_regalias", "NUMERIC"),
        bigquery.SchemaField("recursos_propios_territorial", "NUMERIC"),
        bigquery.SchemaField("recursos_de_credito", "NUMERIC"),
        bigquery.SchemaField("recursos_propios", "NUMERIC"),
        # Flags
        bigquery.SchemaField("habilita_pago_adelantado", "STRING"),
        bigquery.SchemaField("liquidacion", "STRING"),
        bigquery.SchemaField("obligacion_ambiental", "STRING"),
        bigquery.SchemaField("obligaciones_postconsumo", "STRING"),
        bigquery.SchemaField("reversion", "STRING"),
        bigquery.SchemaField("espostconflicto", "STRING"),
        bigquery.SchemaField("dias_adicionados", "INT64"),
        bigquery.SchemaField("puntos_del_acuerdo", "STRING"),
        bigquery.SchemaField("pilares_del_acuerdo", "STRING"),
        bigquery.SchemaField("el_contrato_puede_ser_prorrogado", "STRING"),
        # URL
        bigquery.SchemaField("urlproceso", "STRING"),
        # Representante legal
        bigquery.SchemaField("nombre_representante_legal", "STRING"),
        bigquery.SchemaField("nacionalidad_representante_legal", "STRING"),
        bigquery.SchemaField("domicilio_representante_legal", "STRING"),
        bigquery.SchemaField("tipo_identificacion_representante_legal", "STRING"),
        bigquery.SchemaField("identificacion_representante_legal", "STRING"),
        bigquery.SchemaField("genero_representante_legal", "STRING"),
        # Ordenador del gasto
        bigquery.SchemaField("nombre_ordenador_del_gasto", "STRING"),
        bigquery.SchemaField("tipo_documento_ordenador_del_gasto", "STRING"),
        bigquery.SchemaField("numero_documento_ordenador_del_gasto", "STRING"),
        # Supervisor
        bigquery.SchemaField("nombre_supervisor", "STRING"),
        bigquery.SchemaField("tipo_documento_supervisor", "STRING"),
        bigquery.SchemaField("numero_documento_supervisor", "STRING"),
        # Ordenador de pago
        bigquery.SchemaField("nombre_ordenador_de_pago", "STRING"),
        bigquery.SchemaField("tipo_documento_ordenador_de_pago", "STRING"),
        bigquery.SchemaField("numero_documento_ordenador_de_pago", "STRING"),
        # Bancario
        bigquery.SchemaField("nombre_del_banco", "STRING"),
        bigquery.SchemaField("tipo_de_cuenta", "STRING"),
        bigquery.SchemaField("numero_de_cuenta", "STRING"),
        # Documentos tipo
        bigquery.SchemaField("documentos_tipo", "STRING"),
        bigquery.SchemaField("descripcion_documentos_tipo", "STRING"),
        # Metadata
        bigquery.SchemaField("_ingested_at", "TIMESTAMP"),
        bigquery.SchemaField("_source_hash", "STRING"),
    ]

    table = bigquery.Table(FULL_TABLE_ID, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.MONTH,
        field="fecha_de_firma"
    )
    table.clustering_fields = ["departamento", "nombre_entidad", "estado_contrato"]
    table.description = "Contratos electrónicos SECOP II - Datos Abiertos Colombia"

    client.create_table(table)
    logger.info(f"Table {FULL_TABLE_ID} created with partitioning and clustering")


def load_to_bigquery(client: bigquery.Client, records: list):
    """Load transformed records into BigQuery using load job (more efficient than streaming)."""
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

    job = client.load_table_from_json(
        records,
        FULL_TABLE_ID,
        job_config=job_config,
    )
    job.result()  # Wait for completion

    return len(records)


def get_current_count(client: bigquery.Client) -> int:
    """Get current row count from BigQuery table."""
    try:
        query = f"SELECT COUNT(*) as cnt FROM `{FULL_TABLE_ID}`"
        result = list(client.query(query).result())
        return result[0].cnt
    except Exception:
        return 0


def main():
    logger.info("=" * 60)
    logger.info("Odin v2 - SECOP II Initial Load")
    logger.info("=" * 60)

    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID)

    # Ensure dataset and table exist
    ensure_dataset(client)
    ensure_table(client)

    # Check if we're resuming
    current_count = get_current_count(client)
    start_offset = current_count
    if current_count > 0:
        logger.info(f"Resuming from offset {current_count} (existing rows in BQ)")
    else:
        logger.info("Starting fresh load from offset 0")

    # Get total count from API
    try:
        resp = requests.get(f"{SODA_API_BASE}?$select=count(*)", timeout=30)
        total = int(resp.json()[0]["count"])
        logger.info(f"Total records in SECOP II API: {total:,}")
    except Exception as e:
        logger.warning(f"Could not get total count: {e}. Using estimate.")
        total = 5_700_000

    # Fetch and load in batches
    offset = start_offset
    total_loaded = 0
    batch_num = 0
    start_time = time.time()

    while offset < total:
        batch_num += 1
        logger.info(f"[Batch {batch_num}] Fetching offset {offset:,} / {total:,} ({offset/total*100:.1f}%)")

        # Fetch from API
        raw_records = fetch_page(offset, BATCH_SIZE)
        if not raw_records:
            logger.info("No more records. Finished.")
            break

        # Transform
        transformed = []
        for raw in raw_records:
            try:
                transformed.append(transform_record(raw))
            except Exception as e:
                logger.warning(f"Failed to transform record: {e}")
                continue

        # Load to BigQuery
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
