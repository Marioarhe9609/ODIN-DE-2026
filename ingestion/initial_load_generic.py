"""
Odin v2 - Universal Initial Load for SECOP II Datasets
A single script that loads ANY SECOP II dataset into BigQuery.
Usage: python initial_load_generic.py <dataset_key>
       python initial_load_generic.py ALL

Features:
- Resume-capable (checkpointing via BigQuery COUNT)
- Auto-detects schema from API
- Preserves existing BigQuery types
- Adds new fields as STRING automatically
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
BATCH_SIZE = 50000
REQUEST_DELAY = 0.5
MAX_RETRIES = 5

# ─── All SECOP II Datasets ──────────────────────────────────────────────────
DATASETS = {
    "proponentes": {
        "soda_id": "hgi6-6wh3",
        "table_name": "proponentes_proceso",
        "description": "Proponentes por Proceso SECOP II",
        "merge_key": None,  # No single unique key — use hash
        "date_field": "fecha_publicaci_n",
    },
    "modificaciones": {
        "soda_id": "u8cx-r425",
        "table_name": "modificaciones_contratos",
        "description": "Modificaciones a Contratos SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "adiciones": {
        "soda_id": "cb9c-h8sn",
        "table_name": "adiciones",
        "description": "Adiciones a Contratos SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "multas_sanciones": {
        "soda_id": "it5q-hg94",
        "table_name": "multas_sanciones",
        "description": "Multas y Sanciones SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "suspensiones": {
        "soda_id": "u99c-7mfm",
        "table_name": "suspensiones_contratos",
        "description": "Suspensiones de Contratos SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "compromisos": {
        "soda_id": "skc9-met7",
        "table_name": "compromisos_presupuestales",
        "description": "Compromisos Presupuestales SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "cdps": {
        "soda_id": "a86w-fh92",
        "table_name": "solicitudes_cdps",
        "description": "Solicitudes CDPs SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "plan_anual": {
        "soda_id": "9sue-ezhx",
        "table_name": "plan_anual_adquisiciones",
        "description": "Plan Anual de Adquisiciones Detalle SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "grupos_proveedores": {
        "soda_id": "ceth-n4bn",
        "table_name": "grupos_proveedores",
        "description": "Grupos de Proveedores SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
    "facturas": {
        "soda_id": "ibyt-yi2f",
        "table_name": "facturas",
        "description": "Facturas SECOP II",
        "merge_key": None,
        "date_field": ":updated_at",
    },
}

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("initial_load_generic.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def compute_hash(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def transform_record(raw: dict) -> dict:
    """Generic transform: clean field names, add metadata."""
    record = {}
    now = datetime.now(timezone.utc).isoformat()

    for key, value in raw.items():
        # Skip SODA metadata fields
        if key.startswith(":"):
            continue

        # Handle URL-type fields (nested dicts)
        if isinstance(value, dict) and "url" in value:
            value = value.get("url", "")

        # Clean field name: lowercase, remove trailing underscores
        clean_key = key.lower().strip("_")
        record[clean_key] = value

    record["_ingested_at"] = now
    record["_source_hash"] = compute_hash(raw)
    return record


def get_total_count(soda_id: str) -> int:
    """Get total record count from the API."""
    url = f"https://www.datos.gov.co/resource/{soda_id}.json"
    params = {"$select": "count(*) as count"}
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return int(data[0]["count"])
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"Count query failed (attempt {attempt+1}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    return 0


def fetch_page(soda_id: str, offset: int, limit: int = BATCH_SIZE) -> list:
    """Fetch a page of records from the SODA API."""
    url = f"https://www.datos.gov.co/resource/{soda_id}.json"
    params = {"$limit": limit, "$offset": offset, "$order": ":id"}
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt
            logger.warning(f"Fetch failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    logger.error(f"Failed to fetch offset {offset} after {MAX_RETRIES} retries")
    return []


def ensure_table(client: bigquery.Client, full_table_id: str, soda_id: str):
    """Create the table if it doesn't exist, using a sample from the API to detect schema."""
    try:
        client.get_table(full_table_id)
        logger.info(f"  Table {full_table_id} already exists")
        return
    except NotFound:
        pass

    logger.info(f"  Creating table {full_table_id}...")

    # Fetch a small sample to detect fields
    sample = fetch_page(soda_id, 0, limit=100)
    if not sample:
        logger.error("  Cannot create table: no sample data available")
        sys.exit(1)

    # Detect all field names from sample
    all_fields = set()
    for rec in sample:
        transformed = transform_record(rec)
        all_fields.update(transformed.keys())

    # Build schema: everything as STRING except metadata fields
    schema = []
    for field in sorted(all_fields):
        if field == "_ingested_at":
            schema.append(bigquery.SchemaField(field, "TIMESTAMP"))
        elif field == "_source_hash":
            schema.append(bigquery.SchemaField(field, "STRING"))
        else:
            schema.append(bigquery.SchemaField(field, "STRING"))

    table = bigquery.Table(full_table_id, schema=schema)
    table = client.create_table(table)
    logger.info(f"  [OK] Created table with {len(schema)} fields")


def get_bq_count(client: bigquery.Client, full_table_id: str) -> int:
    """Get current row count from BigQuery."""
    try:
        query = f"SELECT COUNT(*) as cnt FROM `{full_table_id}`"
        result = client.query(query).result()
        for row in result:
            return row.cnt
    except Exception:
        return 0


def load_to_bigquery(client: bigquery.Client, records: list, full_table_id: str):
    """Load records to BigQuery with schema-aware type preservation."""
    if not records:
        return 0

    # Get current table schema to preserve existing types
    table = client.get_table(full_table_id)
    existing_fields = {f.name: f for f in table.schema}

    # Detect new fields
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())
    new_fields = all_keys - set(existing_fields.keys())

    # Build extended schema
    extended_schema = list(table.schema)
    if new_fields:
        for field_name in sorted(new_fields):
            extended_schema.append(bigquery.SchemaField(field_name, "STRING"))
            logger.info(f"  [+] New field: {field_name}")

    # Force STRING values to str to avoid type conflicts
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
    job = client.load_table_from_json(records, full_table_id, job_config=job_config)
    job.result()
    return len(records)


def load_dataset(key: str, config: dict):
    """Run initial load for a single dataset."""
    soda_id = config["soda_id"]
    table_name = config["table_name"]
    full_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    logger.info("=" * 60)
    logger.info(f"Loading: {config['description']}")
    logger.info(f"  API: {soda_id} -> Table: {full_table_id}")
    logger.info("=" * 60)

    client = bigquery.Client(project=PROJECT_ID)

    # 1. Get total count from API
    total = get_total_count(soda_id)
    logger.info(f"  Total records in API: {total:,}")

    if total == 0:
        logger.warning("  No records found. Skipping.")
        return

    # 2. Ensure table exists
    ensure_table(client, full_table_id, soda_id)

    # 3. Get current count for resume
    current = get_bq_count(client, full_table_id)
    logger.info(f"  Already loaded: {current:,}")
    remaining = total - current

    if remaining <= 0:
        logger.info("  [OK] Already fully loaded!")
        return

    logger.info(f"  Remaining: {remaining:,}")

    # 4. Load in batches
    offset = current
    loaded_this_run = 0
    batch_num = 0
    start_time = time.time()

    while offset < total:
        batch_num += 1
        pct = (offset / total) * 100
        logger.info(f"  [Batch {batch_num}] Fetching offset {offset:,} / {total:,} ({pct:.1f}%)")

        raw_records = fetch_page(soda_id, offset)
        if not raw_records:
            logger.warning("  No records returned. Stopping.")
            break

        transformed = [transform_record(r) for r in raw_records]

        try:
            loaded = load_to_bigquery(client, transformed, full_table_id)
            loaded_this_run += loaded
            offset += len(raw_records)
            logger.info(f"  [Batch {batch_num}] Loaded {loaded:,} records (total this run: {loaded_this_run:,})")
        except Exception as e:
            logger.error(f"  [Batch {batch_num}] BigQuery load failed: {e}")
            logger.info("  Saving checkpoint. Resume by re-running this script.")
            break

        time.sleep(REQUEST_DELAY)

    # 5. Summary
    elapsed = (time.time() - start_time) / 60
    final_count = get_bq_count(client, full_table_id)
    logger.info("=" * 60)
    logger.info(f"COMPLETE: {config['description']}")
    logger.info(f"  Total rows in BigQuery: {final_count:,}")
    logger.info(f"  Rows loaded this run: {loaded_this_run:,}")
    logger.info(f"  Time: {elapsed:.1f} minutes")
    logger.info("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python initial_load_generic.py <dataset_key|ALL>")
        print(f"\nAvailable datasets: {', '.join(DATASETS.keys())}")
        sys.exit(1)

    target = sys.argv[1].lower()

    if target == "all":
        # Load all datasets in order (smallest first, plan_anual skipped — run separately)
        order = sorted(DATASETS.keys(), key=lambda k: {
            "multas_sanciones": 1,
            "suspensiones": 2,
            "grupos_proveedores": 3,
            "facturas": 4,
            "proponentes": 5,
            "compromisos": 6,
            "cdps": 7,
            "modificaciones": 8,
            "adiciones": 9,
        }.get(k, 99))
        # Skip plan_anual in ALL mode (19.6M rows, run separately)
        order = [k for k in order if k != "plan_anual"]

        logger.info(f"Loading ALL {len(order)} datasets...")
        for key in order:
            try:
                load_dataset(key, DATASETS[key])
            except Exception as e:
                logger.error(f"Failed to load {key}: {e}")
                logger.info("Continuing with next dataset...")
                continue
    elif target in DATASETS:
        load_dataset(target, DATASETS[target])
    else:
        print(f"Unknown dataset: {target}")
        print(f"Available: {', '.join(DATASETS.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    main()
