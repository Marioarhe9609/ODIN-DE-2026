"""Inspect all tables in the secop dataset and output their schemas."""
import json
from google.cloud import bigquery

PROJECT_ID = "odin-v2-495523"
DATASET_ID = "secop"

client = bigquery.Client(project=PROJECT_ID)

# List all tables
tables = list(client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"))
print(f"Found {len(tables)} tables in {DATASET_ID}\n")

report = {}

for t in sorted(tables, key=lambda x: x.table_id):
    full_id = f"{PROJECT_ID}.{DATASET_ID}.{t.table_id}"
    table = client.get_table(full_id)
    
    # Get row count
    q = f"SELECT COUNT(*) as cnt FROM `{full_id}`"
    rows = list(client.query(q).result())
    count = rows[0].cnt
    
    fields = []
    for f in table.schema:
        fields.append({"name": f.name, "type": f.field_type, "mode": f.mode})
    
    report[t.table_id] = {
        "row_count": count,
        "num_fields": len(fields),
        "size_mb": round(table.num_bytes / 1024 / 1024, 1) if table.num_bytes else 0,
        "fields": fields,
    }
    
    print(f"{'='*60}")
    print(f"TABLE: {t.table_id}")
    print(f"  Rows: {count:,} | Fields: {len(fields)} | Size: {report[t.table_id]['size_mb']} MB")
    print(f"  Fields:")
    for f in fields:
        if f["name"].startswith("_"):
            continue
        print(f"    - {f['name']:50s} {f['type']}")

# Save full report
with open("schema_report.json", "w", encoding="utf-8") as fp:
    json.dump(report, fp, indent=2, ensure_ascii=False)

print(f"\nFull schema saved to schema_report.json")
