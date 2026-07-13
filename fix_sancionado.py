"""Fix sancionado_activo view using correct field names"""
from google.cloud import bigquery
PROJECT = "odin-v2-495523"
DS = "secop"
client = bigquery.Client(project=PROJECT)
T = f"`{PROJECT}.{DS}"

full_id = f"{PROJECT}.{DS}.v_anticorr_sancionado_activo"
v = bigquery.Table(full_id)
v.view_query = f"""
SELECT
  m.nombre_proveedor_objeto_de as proveedor_sancionado,
  m.as_codigo_proveedor_objeto as nit_sancionado,
  m.tipo_de_sancion,
  m.estado as estado_sancion,
  m.fecha_evento as fecha_sancion,
  m.valor as valor_sancion,
  m.nombre_entidad_creadora as entidad_sancionadora,
  c.id_contrato,
  c.nombre_entidad as entidad_contratante,
  c.valor_del_contrato,
  c.fecha_de_firma
FROM {T}.multas_sanciones` m
JOIN {T}.contratos_electronicos` c
  ON m.as_codigo_proveedor_objeto = c.documento_proveedor
WHERE c.fecha_de_firma IS NOT NULL
"""
v.description = "A05: Proveedores sancionados con contratos"
client.delete_table(full_id, not_found_ok=True)
client.create_table(v)
print("[OK] v_anticorr_sancionado_activo")

views = [t for t in client.list_tables(f"{PROJECT}.{DS}") if t.table_type == "VIEW"]
print(f"Total views: {len(list(views))}")
