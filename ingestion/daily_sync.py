"""
Odin v2 - Unified Daily Sync
Incrementally syncs both SECOP II datasets from datos.gov.co into BigQuery:
  1. Contratos Electrónicos (jbjy-vk9h) → secop.contratos_electronicos
  2. Procesos de Contratación (p6dx-8zbt) → secop.procesos_contratacion

Designed to run daily via Cloud Scheduler + Cloud Run Job.
Uses incremental fetch by date + MERGE for upsert.
"""

import json
import hashlib
import time
import logging
import sys
from datetime import datetime, timezone, timedelta

import requests
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# ─── Configuration ───────────────────────────────────────────────────────────
PROJECT_ID = "odin-v2-495523"
DATASET_ID = "secop"
SYNC_STATE_TABLE = f"{PROJECT_ID}.{DATASET_ID}.sync_state"

BATCH_SIZE = 50000
REQUEST_DELAY = 0.5
MAX_RETRIES = 5

# ─── Dataset Definitions ────────────────────────────────────────────────────
DATASETS = {
    "contratos_electronicos": {
        "soda_url": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.contratos_electronicos",
        "date_field": "ultima_actualizacion",
        "merge_key": "id_contrato",
        "transform_fn": "transform_contrato",
    },
    "procesos_contratacion": {
        "soda_url": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.procesos_contratacion",
        "date_field": "fecha_de_ultima_publicaci",
        "merge_key": "id_del_proceso",
        "transform_fn": "transform_proceso",
    },
    "proponentes_proceso": {
        "soda_url": "https://www.datos.gov.co/resource/hgi6-6wh3.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.proponentes_proceso",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "modificaciones_contratos": {
        "soda_url": "https://www.datos.gov.co/resource/u8cx-r425.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.modificaciones_contratos",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "adiciones": {
        "soda_url": "https://www.datos.gov.co/resource/cb9c-h8sn.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.adiciones",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "multas_sanciones": {
        "soda_url": "https://www.datos.gov.co/resource/it5q-hg94.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.multas_sanciones",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "suspensiones_contratos": {
        "soda_url": "https://www.datos.gov.co/resource/u99c-7mfm.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.suspensiones_contratos",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "compromisos_presupuestales": {
        "soda_url": "https://www.datos.gov.co/resource/skc9-met7.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.compromisos_presupuestales",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "solicitudes_cdps": {
        "soda_url": "https://www.datos.gov.co/resource/a86w-fh92.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.solicitudes_cdps",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "plan_anual_adquisiciones": {
        "soda_url": "https://www.datos.gov.co/resource/9sue-ezhx.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.plan_anual_adquisiciones",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "grupos_proveedores": {
        "soda_url": "https://www.datos.gov.co/resource/ceth-n4bn.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.grupos_proveedores",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "facturas": {
        "soda_url": "https://www.datos.gov.co/resource/ibyt-yi2f.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.facturas",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_generic",
    },
    "tienda_virtual_consolidado": {
        "soda_url": "https://www.datos.gov.co/resource/rgxm-mmea.json",
        "table_id": f"{PROJECT_ID}.{DATASET_ID}.tienda_virtual_consolidado",
        "date_field": ":updated_at",
        "merge_key": "_source_hash",
        "transform_fn": "transform_tvec",
    },
}

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daily_sync.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSFORM FUNCTIONS (one per dataset)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Contratos Electrónicos ───────────────────────────────────────────────────
CONTRATO_FIELD_MAP = {
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

CONTRATO_TIMESTAMP_FIELDS = {
    "fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato",
    "fecha_inicio_liquidacion", "fecha_fin_liquidacion", "ultima_actualizacion",
    "fecha_de_notificacion_de_prorrogacion",
}

CONTRATO_NUMERIC_FIELDS = {
    "valor_del_contrato", "valor_de_pago_adelantado", "valor_facturado",
    "valor_pendiente_de_pago", "valor_pagado", "valor_amortizado",
    "valor_pendiente_de_amortizacion", "valor_pendiente_de_ejecucion",
    "saldo_cdp", "saldo_vigencia", "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regalias",
    "recursos_propios_territorial", "recursos_de_credito", "recursos_propios",
}

CONTRATO_INTEGER_FIELDS = {"codigo_entidad", "dias_adicionados"}


def transform_contrato(raw: dict) -> dict:
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for api_key, value in raw.items():
        bq_key = CONTRATO_FIELD_MAP.get(api_key, api_key)
        if bq_key == "urlproceso" and isinstance(value, dict):
            value = value.get("url", "")
        if bq_key.startswith(":"):
            continue
        record[bq_key] = value

    _apply_types(record, CONTRATO_TIMESTAMP_FIELDS, CONTRATO_NUMERIC_FIELDS, CONTRATO_INTEGER_FIELDS)

    if "nit_entidad" in record:
        record["nit_entidad"] = str(record["nit_entidad"]) if record["nit_entidad"] else None

    record["_ingested_at"] = now
    record["_source_hash"] = _hash(raw)
    return record


# ── Procesos de Contratación ─────────────────────────────────────────────────
PROCESO_FIELD_MAP = {
    "descripci_n_del_procedimiento": "descripcion_del_procedimiento",
    "fecha_de_publicacion_del": "fecha_de_publicacion_del_proceso",
    "fecha_de_ultima_publicaci": "fecha_de_ultima_publicacion",
    "fecha_de_publicacion_fase": "fecha_publicacion_fase_planeacion_precalif",
    "fecha_de_publicacion_fase_1": "fecha_publicacion_fase_seleccion_precalif",
    "fecha_de_publicacion": "fecha_publicacion_manifestacion_interes",
    "fecha_de_publicacion_fase_2": "fecha_publicacion_fase_borrador",
    "fecha_de_publicacion_fase_3": "fecha_publicacion_fase_seleccion",
    "justificaci_n_modalidad_de": "justificacion_modalidad_de_contratacion",
    "ciudad_de_la_unidad_de": "ciudad_unidad_contratacion",
    "nombre_de_la_unidad_de": "nombre_unidad_contratacion",
    "proveedores_con_invitacion": "proveedores_con_invitacion_directa",
    "visualizaciones_del": "visualizaciones_del_procedimiento",
    "proveedores_que_manifestaron": "proveedores_que_manifestaron_interes",
    "conteo_de_respuestas_a_ofertas": "conteo_respuestas_ofertas",
    "proveedores_unicos_con": "proveedores_unicos_con_respuesta",
    "codigo_principal_de_categoria": "codigo_principal_de_categoria",
    "estado_de_apertura_del_proceso": "estado_de_apertura_del_proceso",
    "codigo_pci": "entidad_centralizada",
    "ordenentidad": "orden_entidad",
    "entidad": "nombre_entidad",
    "codigoproveedor": "codigo_proveedor",
}

PROCESO_TIMESTAMP_FIELDS = {
    "fecha_de_publicacion_del_proceso", "fecha_de_ultima_publicacion",
    "fecha_publicacion_fase_planeacion_precalif", "fecha_publicacion_fase_seleccion_precalif",
    "fecha_publicacion_manifestacion_interes", "fecha_publicacion_fase_borrador",
    "fecha_publicacion_fase_seleccion",
}

PROCESO_NUMERIC_FIELDS = {"precio_base", "valor_total_adjudicacion"}

PROCESO_INTEGER_FIELDS = {
    "duracion", "proveedores_invitados", "proveedores_con_invitacion_directa",
    "visualizaciones_del_procedimiento", "proveedores_que_manifestaron_interes",
    "respuestas_al_procedimiento", "respuestas_externas",
    "conteo_respuestas_ofertas", "proveedores_unicos_con_respuesta",
    "numero_de_lotes", "codigo_entidad",
}


def transform_proceso(raw: dict) -> dict:
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for api_key, value in raw.items():
        bq_key = PROCESO_FIELD_MAP.get(api_key, api_key)
        if bq_key == "urlproceso" and isinstance(value, dict):
            value = value.get("url", "")
        if bq_key.startswith(":"):
            continue
        record[bq_key] = value

    _apply_types(record, PROCESO_TIMESTAMP_FIELDS, PROCESO_NUMERIC_FIELDS, PROCESO_INTEGER_FIELDS)

    record["_ingested_at"] = now
    record["_source_hash"] = _hash(raw)
    return record


# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _hash(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _apply_types(record: dict, ts_fields: set, num_fields: set, int_fields: set):
    """Apply type conversions in-place."""
    for field in ts_fields:
        if field in record:
            val = record[field]
            if not val or not isinstance(val, str) or not val.strip():
                record[field] = None

    for field in num_fields:
        if field in record:
            try:
                val = record[field]
                if val is not None and str(val).strip():
                    record[field] = float(str(val).replace(",", ""))
                else:
                    record[field] = None
            except (ValueError, TypeError):
                record[field] = None

    for field in int_fields:
        if field in record:
            try:
                val = record[field]
                if val is not None and str(val).strip():
                    record[field] = int(float(str(val)))
                else:
                    record[field] = None
            except (ValueError, TypeError):
                record[field] = None


# ── Generic Transform (for new datasets) ────────────────────────────────────
def transform_generic(raw: dict) -> dict:
    """Generic transform: clean field names, stringify all values, add metadata."""
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for key, value in raw.items():
        if key.startswith(":"):
            continue
        if isinstance(value, dict) and "url" in value:
            value = value.get("url", "")
        clean_key = key.lower().strip("_")
        # Force everything to string for safety
        if value is not None:
            record[clean_key] = str(value)
        else:
            record[clean_key] = None

    record["_ingested_at"] = now
    record["_source_hash"] = _hash(raw)
    return record


def transform_tvec(raw: dict) -> dict:
    """Transform for Tienda Virtual dataset: parse dates/floats properly, stringify others."""
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for key, value in raw.items():
        if key.startswith(":"):
            continue
        clean_key = key.lower().strip("_")
        
        # Handle field names mapping if needed (año -> a_o is handled by Socrata as a_o)
        if value is not None:
            if clean_key in ("fecha", "fecha_vence"):
                # BigQuery expects standard timestamp formatting
                # Socrata returns: "2021-06-03T00:00:00.000"
                record[clean_key] = str(value)
            elif clean_key == "total":
                try:
                    record[clean_key] = float(str(value).replace(",", ""))
                except (ValueError, TypeError):
                    record[clean_key] = None
            else:
                record[clean_key] = str(value)
        else:
            record[clean_key] = None

    record["_ingested_at"] = now
    record["_source_hash"] = _hash(raw)
    return record


TRANSFORM_REGISTRY = {
    "transform_contrato": transform_contrato,
    "transform_proceso": transform_proceso,
    "transform_generic": transform_generic,
    "transform_tvec": transform_tvec,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SYNC ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_sync_state_table(client: bigquery.Client):
    schema = [
        bigquery.SchemaField("sync_id", "STRING"),
        bigquery.SchemaField("dataset_name", "STRING"),
        bigquery.SchemaField("last_sync_timestamp", "TIMESTAMP"),
        bigquery.SchemaField("records_synced", "INT64"),
        bigquery.SchemaField("sync_started_at", "TIMESTAMP"),
        bigquery.SchemaField("sync_completed_at", "TIMESTAMP"),
        bigquery.SchemaField("status", "STRING"),
    ]
    table = bigquery.Table(SYNC_STATE_TABLE, schema=schema)
    try:
        client.get_table(SYNC_STATE_TABLE)
    except NotFound:
        client.create_table(table)
        logger.info("Created sync_state table")


def get_last_sync_timestamp(client: bigquery.Client, dataset_name: str) -> str:
    try:
        query = f"""
            SELECT last_sync_timestamp
            FROM `{SYNC_STATE_TABLE}`
            WHERE status = 'completed' AND dataset_name = '{dataset_name}'
            ORDER BY sync_completed_at DESC
            LIMIT 1
        """
        results = list(client.query(query).result())
        if results and results[0].last_sync_timestamp:
            return results[0].last_sync_timestamp.strftime("%Y-%m-%dT%H:%M:%S.000")
    except Exception as e:
        logger.warning(f"Could not get last sync for {dataset_name}: {e}")

    # Default: last 2 days
    default = datetime.now(timezone.utc) - timedelta(days=2)
    return default.strftime("%Y-%m-%dT%H:%M:%S.000")


def save_sync_state(client: bigquery.Client, sync_id: str, dataset_name: str,
                    last_ts: str, records: int, started: str, status: str):
    now = datetime.now(timezone.utc).isoformat()
    rows = [{
        "sync_id": sync_id,
        "dataset_name": dataset_name,
        "last_sync_timestamp": last_ts,
        "records_synced": records,
        "sync_started_at": started,
        "sync_completed_at": now,
        "status": status,
    }]
    client.insert_rows_json(SYNC_STATE_TABLE, rows)


def fetch_updated_records(soda_url: str, date_field: str, since: str) -> list:
    """Fetch all records updated since the given timestamp."""
    all_records = []
    offset = 0
    where_clause = f"{date_field} > '{since}'"

    while True:
        params = {
            "$limit": BATCH_SIZE,
            "$offset": offset,
            "$order": ":id",
            "$where": where_clause,
        }

        data = []
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(soda_url, params=params, timeout=120)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.RequestException as e:
                wait = 2 ** attempt
                logger.warning(f"Request failed (attempt {attempt+1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

        if not data:
            break

        all_records.extend(data)
        logger.info(f"  Fetched {len(data)} records (total: {len(all_records)})")

        if len(data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE
        time.sleep(REQUEST_DELAY)

    return all_records


def upsert_to_bigquery(client: bigquery.Client, table_id: str, merge_key: str, records: list) -> int:
    """Upsert records into BigQuery using staging table + MERGE.
    Auto-detects new fields from the API and adds them to the main table."""
    if not records:
        return 0

    staging_id = table_id + "_staging"

    # Cleanup any leftover staging table
    client.delete_table(staging_id, not_found_ok=True)

    # ── Step 1: Load to staging with autodetect to capture ALL fields ────
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
    )
    job = client.load_table_from_json(records, staging_id, job_config=job_config)
    job.result()
    logger.info(f"  Loaded {len(records)} records to staging (autodetect)")

    # ── Step 2: Detect new columns ───────────────────────────────────────
    main_table = client.get_table(table_id)
    staging_table = client.get_table(staging_id)

    main_columns = {f.name for f in main_table.schema}
    staging_columns = {f.name for f in staging_table.schema}
    new_columns = staging_columns - main_columns

    if new_columns:
        # Build ALTER TABLE to add new columns as STRING (safe default)
        for col_name in sorted(new_columns):
            alter_query = f"ALTER TABLE `{table_id}` ADD COLUMN `{col_name}` STRING"
            try:
                client.query(alter_query).result()
                logger.info(f"  📌 Added new column to main table: {col_name}")
            except Exception as e:
                logger.warning(f"  Could not add column {col_name}: {e}")

        # Refresh main table schema after alterations
        main_table = client.get_table(table_id)

    # ── Step 3: Build MERGE with type-safe casting ─────────────────────
    # Build type maps to handle autodetect type mismatches (e.g. BOOL vs STRING)
    main_type_map = {f.name: f.field_type for f in main_table.schema}
    staging_type_map = {f.name: f.field_type for f in staging_table.schema}

    main_cols_updated = set(main_type_map.keys())
    staging_cols = set(staging_type_map.keys())
    shared_columns = sorted(main_cols_updated & staging_cols)

    # Exclude _ingested_at from SET (we override it with CURRENT_TIMESTAMP)
    merge_columns = [c for c in shared_columns if c != "_ingested_at"]

    def _col_ref(col_name: str) -> str:
        """Return S.`col` with CAST if types differ between staging and main."""
        main_type = main_type_map.get(col_name)
        staging_type = staging_type_map.get(col_name)
        if main_type and staging_type and main_type != staging_type:
            return f"CAST(S.`{col_name}` AS {main_type})"
        return f"S.`{col_name}`"

    set_clause = ", ".join(f"T.`{c}` = {_col_ref(c)}" for c in merge_columns)
    set_clause += ", T._ingested_at = CURRENT_TIMESTAMP()"
    insert_cols = ", ".join(f"`{c}`" for c in merge_columns) + ", _ingested_at"
    insert_vals = ", ".join(_col_ref(c) for c in merge_columns) + ", CURRENT_TIMESTAMP()"

    merge_query = f"""
        MERGE `{table_id}` T
        USING `{staging_id}` S
        ON T.`{merge_key}` = S.`{merge_key}`
        WHEN MATCHED THEN
            UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN
            INSERT ({insert_cols})
            VALUES ({insert_vals})
    """

    job = client.query(merge_query)
    job.result()
    affected = job.num_dml_affected_rows or len(records)
    logger.info(f"  MERGE completed: {affected} rows affected")

    # Cleanup staging
    client.delete_table(staging_id, not_found_ok=True)

    return affected


def sync_dataset(client: bigquery.Client, name: str, config: dict):
    """Sync a single dataset."""
    logger.info(f"{'─' * 50}")
    logger.info(f"Syncing: {name}")
    logger.info(f"{'─' * 50}")

    sync_id = f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    started_at = datetime.now(timezone.utc).isoformat()

    # Get last sync timestamp
    last_sync = get_last_sync_timestamp(client, name)
    logger.info(f"  Last sync: {last_sync}")

    # Fetch updated records from API
    logger.info(f"  Fetching from {config['soda_url']}...")
    raw_records = fetch_updated_records(
        config["soda_url"],
        config["date_field"],
        last_sync,
    )
    logger.info(f"  Found {len(raw_records):,} updated records")

    if not raw_records:
        logger.info(f"  No new records for {name}. Skipping.")
        save_sync_state(client, sync_id, name, last_sync, 0, started_at, "completed")
        return 0

    # Transform
    transform_fn = TRANSFORM_REGISTRY[config["transform_fn"]]
    transformed = []
    for raw in raw_records:
        try:
            transformed.append(transform_fn(raw))
        except Exception as e:
            logger.warning(f"  Transform failed: {e}")

    # Upsert
    try:
        affected = upsert_to_bigquery(
            client, config["table_id"], config["merge_key"], transformed
        )
        new_sync_ts = datetime.now(timezone.utc).isoformat()
        save_sync_state(client, sync_id, name, new_sync_ts, affected, started_at, "completed")
        logger.info(f"  ✅ {name}: {affected:,} rows synced")
        return affected
    except Exception as e:
        logger.error(f"  ❌ {name} sync failed: {e}")
        save_sync_state(client, sync_id, name, last_sync, 0, started_at, "failed")
        raise


def main():
    logger.info("=" * 60)
    logger.info("Odin v2 - Unified Daily Sync")
    logger.info(f"Started: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    client = bigquery.Client(project=PROJECT_ID)
    ensure_sync_state_table(client)

    total_synced = 0
    results = {}

    for name, config in DATASETS.items():
        try:
            affected = sync_dataset(client, name, config)
            results[name] = {"status": "success", "rows": affected}
            total_synced += affected
        except Exception as e:
            results[name] = {"status": "failed", "error": str(e)}
            logger.error(f"Dataset {name} failed: {e}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("DAILY SYNC SUMMARY")
    logger.info("=" * 60)
    for name, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        rows = result.get("rows", 0)
        logger.info(f"  {status} {name}: {rows:,} rows")
    logger.info(f"  Total synced: {total_synced:,} rows")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
