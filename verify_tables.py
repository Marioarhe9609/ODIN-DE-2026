"""
Odin v2 - Phase 2: Create Analytical Views in BigQuery
Creates pre-computed views that the MCP servers will query.
"""
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DS = "secop"
client = bigquery.Client(project=PROJECT)

# ── 1. Verify all tables ──────────────────────────────────────────────────
print("=" * 60)
print("VERIFICANDO TABLAS CARGADAS")
print("=" * 60)
tables = list(client.list_tables(f"{PROJECT}.{DS}"))
for t in sorted(tables, key=lambda x: x.table_id):
    if t.table_id == "sync_state":
        continue
    full = f"{PROJECT}.{DS}.{t.table_id}"
    r = list(client.query(f"SELECT COUNT(*) c FROM `{full}`").result())
    print(f"  {t.table_id:40s} {r[0].c:>15,} rows")

print(f"\nTotal: {len([t for t in tables if t.table_id != 'sync_state'])} tables")
print("=" * 60)
