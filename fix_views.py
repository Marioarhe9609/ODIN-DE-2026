"""Fix the 3 failed views"""
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DS = "secop"
client = bigquery.Client(project=PROJECT)
T = f"`{PROJECT}.{DS}"

def create_view(name, sql, desc):
    full_id = f"{PROJECT}.{DS}.{name}"
    v = bigquery.Table(full_id)
    v.view_query = sql
    v.description = desc
    client.delete_table(full_id, not_found_ok=True)
    try:
        client.create_table(v)
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [ERR] {name}: {e}")

# Fix: multas_sanciones uses different field names - check actual fields
q = f"SELECT * FROM {T}.multas_sanciones` LIMIT 1"
r = list(client.query(q).result())
if r:
    print("multas_sanciones fields:", list(dict(r[0]).keys()))

q2 = f"SELECT * FROM {T}.modificaciones_contratos` LIMIT 1"
r2 = list(client.query(q2).result())
if r2:
    print("modificaciones fields:", list(dict(r2[0]).keys()))

# Fix v_anticorr_sancionado_activo - use correct field names from multas
create_view("v_anticorr_sancionado_activo", f"""
SELECT
  m.*,
  c.id_contrato,
  c.nombre_entidad,
  c.valor_del_contrato,
  c.fecha_de_firma as fecha_contrato_posterior
FROM {T}.multas_sanciones` m
JOIN {T}.contratos_electronicos` c
  ON CAST(m.nit_proveedor AS STRING) = c.documento_proveedor
WHERE c.fecha_de_firma IS NOT NULL
""", "A05: Proveedores sancionados con contratos")

# Fix v_anticorr_modificaciones - use correct field names
create_view("v_anticorr_modificaciones", f"""
SELECT
  m.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  c.fecha_de_firma,
  COUNT(*) as num_modificaciones
FROM {T}.modificaciones_contratos` m
JOIN {T}.contratos_electronicos` c ON m.id_contrato = c.id_contrato
GROUP BY m.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato, c.fecha_de_firma
HAVING COUNT(*) > 5
""", "A08: Contratos con mas de 5 modificaciones")

# Fix v_gasto_por_modalidad - fix PARTITION BY
create_view("v_gasto_por_modalidad", f"""
SELECT
  nombre_entidad,
  departamento,
  modalidad_de_contratacion,
  EXTRACT(YEAR FROM fecha_de_firma) as anio,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_total,
  AVG(valor_del_contrato) as valor_promedio
FROM {T}.contratos_electronicos`
WHERE valor_del_contrato > 0 AND modalidad_de_contratacion IS NOT NULL
GROUP BY nombre_entidad, departamento, modalidad_de_contratacion, anio
""", "Distribucion del gasto por modalidad")

# Final count
views = [t for t in client.list_tables(f"{PROJECT}.{DS}") if t.table_type == "VIEW"]
print(f"\nTotal views: {len(list(views))}")
