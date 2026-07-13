"""
Odin v2 - Phase 2: Create Analytical Views in BigQuery
Views organized by MCP Server:
  - v_anticorr_*  : Anticorrupcion (14 tools)
  - v_gasto_*     : Gasto Publico (7 tools)
  - v_mercado_*   : Inteligencia de Mercado (6 tools)
"""
from google.cloud import bigquery

PROJECT = "odin-v2-495523"
DS = "secop"
client = bigquery.Client(project=PROJECT)

def create_view(view_name: str, sql: str, description: str):
    full_id = f"{PROJECT}.{DS}.{view_name}"
    view = bigquery.Table(full_id)
    view.view_query = sql
    view.description = description
    try:
        client.delete_table(full_id, not_found_ok=True)
        client.create_table(view)
        print(f"  [OK] {view_name}")
    except Exception as e:
        print(f"  [ERR] {view_name}: {e}")

T = f"`{PROJECT}.{DS}"  # shortcut for table refs

# ═══════════════════════════════════════════════════════════════════════════
#  MCP 1: ANTICORRUPCION VIEWS
# ═══════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("MCP 1: ANTICORRUPCION")
print("=" * 60)

# A01 - Proveedor monopolista: % contratos por proveedor-entidad
create_view("v_anticorr_monopolista", f"""
SELECT
  nombre_entidad,
  documento_proveedor,
  proveedor_adjudicado,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_total,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY nombre_entidad), 2) as pct_contratos_entidad,
  MIN(fecha_de_firma) as primer_contrato,
  MAX(fecha_de_firma) as ultimo_contrato
FROM {T}.contratos_electronicos`
WHERE documento_proveedor IS NOT NULL AND nombre_entidad IS NOT NULL
GROUP BY nombre_entidad, documento_proveedor, proveedor_adjudicado
HAVING COUNT(*) >= 5
""", "A01: Proveedores con concentracion de contratos por entidad")

# A02 - Fraccionamiento: minimas cuantias al mismo proveedor/entidad/mes
create_view("v_anticorr_fraccionamiento", f"""
SELECT
  nombre_entidad,
  documento_proveedor,
  proveedor_adjudicado,
  FORMAT_TIMESTAMP('%Y-%m', fecha_de_firma) as mes,
  COUNT(*) as num_contratos_minima,
  SUM(valor_del_contrato) as valor_total_sumado,
  AVG(valor_del_contrato) as valor_promedio
FROM {T}.contratos_electronicos`
WHERE modalidad_de_contratacion LIKE '%nima%'
  AND documento_proveedor IS NOT NULL
  AND fecha_de_firma IS NOT NULL
GROUP BY nombre_entidad, documento_proveedor, proveedor_adjudicado, mes
HAVING COUNT(*) >= 3
""", "A02: Posible fraccionamiento - multiples minimas cuantias")

# A03 - Sin competencia: procesos con 1 proponente (excluyendo directa)
create_view("v_anticorr_sin_competencia", f"""
SELECT
  p.id_del_proceso,
  p.nombre_del_procedimiento,
  p.nombre_entidad,
  p.modalidad_de_contratacion,
  p.precio_base,
  p.valor_total_adjudicacion,
  p.proveedores_unicos_con_respuesta,
  p.fecha_de_publicacion_del_proceso,
  p.nombre_del_proveedor,
  p.nit_del_proveedor_adjudicado
FROM {T}.procesos_contratacion` p
WHERE p.proveedores_unicos_con_respuesta = 1
  AND p.modalidad_de_contratacion NOT LIKE '%irecta%'
  AND p.adjudicado = 'Si'
  AND p.precio_base > 0
""", "A03: Procesos competitivos con un solo proponente")

# A05 - Sancionado activo
create_view("v_anticorr_sancionado_activo", f"""
SELECT
  m.documento_proveedor,
  m.nombre_del_proveedor as nombre_sancionado,
  m.tipo_sanci_n,
  m.estado_sanci_n,
  m.fecha_sanci_n,
  c.id_contrato,
  c.nombre_entidad,
  c.valor_del_contrato,
  c.fecha_de_firma as fecha_contrato_posterior
FROM {T}.multas_sanciones` m
JOIN {T}.contratos_electronicos` c
  ON m.documento_proveedor = c.documento_proveedor
WHERE c.fecha_de_firma > SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', m.fecha_sanci_n)
""", "A05: Proveedores sancionados con contratos posteriores")

# A06 - Adiciones excesivas por contrato
create_view("v_anticorr_adiciones", f"""
SELECT
  a.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  COUNT(*) as num_adiciones,
  COUNT(CASE WHEN a.tipo LIKE '%alor%' THEN 1 END) as adiciones_valor,
  COUNT(CASE WHEN a.tipo LIKE '%lazo%' OR a.tipo LIKE '%iemp%' THEN 1 END) as adiciones_plazo,
  MIN(a.fecharegistro) as primera_adicion,
  MAX(a.fecharegistro) as ultima_adicion
FROM {T}.adiciones` a
JOIN {T}.contratos_electronicos` c ON a.id_contrato = c.id_contrato
GROUP BY a.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato
HAVING COUNT(*) >= 3
""", "A06: Contratos con adiciones excesivas")

# A07 - Suspensiones repetidas
create_view("v_anticorr_suspensiones", f"""
SELECT
  s.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  COUNT(*) as num_suspensiones,
  MIN(s.fecha_de_creacion) as primera_suspension,
  MAX(s.fecha_de_creacion) as ultima_suspension,
  STRING_AGG(DISTINCT s.proposito_de_la_modificacion, ' | ' LIMIT 5) as propositos
FROM {T}.suspensiones_contratos` s
JOIN {T}.contratos_electronicos` c ON s.id_contrato = c.id_contrato
GROUP BY s.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato
HAVING COUNT(*) >= 3
""", "A07: Contratos con 3+ suspensiones")

# A08 - Modificaciones masivas
create_view("v_anticorr_modificaciones", f"""
SELECT
  m.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  c.fecha_de_firma,
  COUNT(*) as num_modificaciones,
  STRING_AGG(DISTINCT m.tipo, ' | ' LIMIT 5) as tipos_modificacion
FROM {T}.modificaciones_contratos` m
JOIN {T}.contratos_electronicos` c ON m.id_contrato = c.id_contrato
GROUP BY m.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato, c.fecha_de_firma
HAVING COUNT(*) > 5
""", "A08: Contratos con mas de 5 modificaciones")

# A09 - Sobrecosto vs precio base
create_view("v_anticorr_sobrecosto", f"""
SELECT
  id_del_proceso,
  nombre_del_procedimiento,
  nombre_entidad,
  modalidad_de_contratacion,
  precio_base,
  valor_total_adjudicacion,
  ROUND((valor_total_adjudicacion - precio_base) * 100.0 / precio_base, 2) as pct_sobrecosto,
  nombre_del_proveedor
FROM {T}.procesos_contratacion`
WHERE precio_base > 0
  AND valor_total_adjudicacion > 0
  AND valor_total_adjudicacion > precio_base * 1.3
  AND adjudicado = 'Si'
""", "A09: Adjudicaciones que superan 30% el precio base")

# A14 - Concentracion en contratacion directa
create_view("v_anticorr_concentracion_directa", f"""
SELECT
  nombre_entidad,
  COUNT(*) as total_contratos,
  SUM(valor_del_contrato) as valor_total,
  SUM(CASE WHEN modalidad_de_contratacion LIKE '%irecta%' THEN valor_del_contrato ELSE 0 END) as valor_directa,
  ROUND(
    SUM(CASE WHEN modalidad_de_contratacion LIKE '%irecta%' THEN valor_del_contrato ELSE 0 END)
    * 100.0 / NULLIF(SUM(valor_del_contrato), 0), 2
  ) as pct_directa
FROM {T}.contratos_electronicos`
WHERE valor_del_contrato > 0
GROUP BY nombre_entidad
HAVING SUM(CASE WHEN modalidad_de_contratacion LIKE '%irecta%' THEN valor_del_contrato ELSE 0 END) * 100.0
       / NULLIF(SUM(valor_del_contrato), 0) > 70
""", "A14: Entidades con >70% del gasto en contratacion directa")

# A23 - Contratos vencidos sin liquidar
create_view("v_anticorr_vencidos", f"""
SELECT
  id_contrato,
  referencia_del_contrato,
  nombre_entidad,
  proveedor_adjudicado,
  valor_del_contrato,
  valor_pendiente_de_ejecucion,
  fecha_de_fin_del_contrato,
  DATE_DIFF(CURRENT_DATE(), CAST(fecha_de_fin_del_contrato AS DATE), DAY) as dias_vencido,
  estado_contrato,
  liquidacion
FROM {T}.contratos_electronicos`
WHERE fecha_de_fin_del_contrato < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
  AND (liquidacion IS NULL OR liquidacion != 'Si')
  AND estado_contrato NOT LIKE '%iquid%'
  AND valor_del_contrato > 0
""", "A23: Contratos vencidos hace mas de 180 dias sin liquidar")

# A24 - Sobrefacturacion
create_view("v_anticorr_sobrefacturacion", f"""
SELECT
  c.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  COALESCE(f.total_facturado, 0) as total_facturado,
  COALESCE(f.num_facturas, 0) as num_facturas,
  ROUND((COALESCE(f.total_facturado, 0) - c.valor_del_contrato) * 100.0 / NULLIF(c.valor_del_contrato, 0), 2) as pct_sobre
FROM {T}.contratos_electronicos` c
JOIN (
  SELECT id_contrato,
         SUM(SAFE_CAST(valor_total AS FLOAT64)) as total_facturado,
         COUNT(*) as num_facturas
  FROM {T}.facturas`
  WHERE valor_total IS NOT NULL
  GROUP BY id_contrato
) f ON c.id_contrato = f.id_contrato
WHERE c.valor_del_contrato > 0
  AND f.total_facturado > c.valor_del_contrato * 1.1
""", "A24: Contratos con facturacion superior al valor contratado")

# ═══════════════════════════════════════════════════════════════════════════
#  MCP 2: GASTO PUBLICO VIEWS
# ═══════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("MCP 2: GASTO PUBLICO")
print("=" * 60)

# Tabla de ejecucion por entidad
create_view("v_gasto_ejecucion_entidad", f"""
SELECT
  nombre_entidad,
  departamento,
  EXTRACT(YEAR FROM fecha_de_firma) as anio,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_asignado,
  SUM(valor_pagado) as valor_pagado,
  SUM(valor_pendiente_de_pago) as valor_pendiente,
  SUM(valor_pendiente_de_ejecucion) as pendiente_ejecucion,
  ROUND(SUM(valor_pagado) * 100.0 / NULLIF(SUM(valor_del_contrato), 0), 2) as pct_ejecucion,
  SUM(valor_facturado) as valor_facturado
FROM {T}.contratos_electronicos`
WHERE valor_del_contrato > 0
GROUP BY nombre_entidad, departamento, anio
""", "Tabla de ejecucion presupuestal: asignado vs pagado vs pendiente")

# Gasto por modalidad
create_view("v_gasto_por_modalidad", f"""
SELECT
  nombre_entidad,
  departamento,
  modalidad_de_contratacion,
  EXTRACT(YEAR FROM fecha_de_firma) as anio,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_total,
  AVG(valor_del_contrato) as valor_promedio,
  ROUND(SUM(valor_del_contrato) * 100.0 / SUM(SUM(valor_del_contrato)) OVER (PARTITION BY nombre_entidad, EXTRACT(YEAR FROM fecha_de_firma)), 2) as pct_del_gasto
FROM {T}.contratos_electronicos`
WHERE valor_del_contrato > 0 AND modalidad_de_contratacion IS NOT NULL
GROUP BY nombre_entidad, departamento, modalidad_de_contratacion, anio
""", "Distribucion del gasto por modalidad de contratacion")

# Gasto temporal (mensual)
create_view("v_gasto_temporal", f"""
SELECT
  FORMAT_TIMESTAMP('%Y-%m', fecha_de_firma) as mes,
  EXTRACT(YEAR FROM fecha_de_firma) as anio,
  nombre_entidad,
  departamento,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_total
FROM {T}.contratos_electronicos`
WHERE fecha_de_firma IS NOT NULL AND valor_del_contrato > 0
GROUP BY mes, anio, nombre_entidad, departamento
""", "Evolucion temporal del gasto mes a mes")

# Resumen CDPs
create_view("v_gasto_cdps", f"""
SELECT
  entidad,
  estado_del_contrato,
  COUNT(*) as num_cdps,
  SUM(SAFE_CAST(saldo_total_a_comprometer AS FLOAT64)) as total_a_comprometer,
  SUM(SAFE_CAST(saldo_cdp AS FLOAT64)) as saldo_cdp,
  SUM(SAFE_CAST(valor_utilizado AS FLOAT64)) as valor_utilizado,
  COUNT(CASE WHEN id_contrato IS NULL OR id_contrato = '' THEN 1 END) as cdps_sin_contrato
FROM {T}.solicitudes_cdps`
WHERE entidad IS NOT NULL
GROUP BY entidad, estado_del_contrato
""", "Resumen de CDPs por entidad y estado")

# Flujo de pagos (facturas x contrato)
create_view("v_gasto_flujo_pagos", f"""
SELECT
  f.id_contrato,
  c.nombre_entidad,
  c.proveedor_adjudicado,
  c.valor_del_contrato,
  COUNT(*) as num_facturas,
  SUM(SAFE_CAST(f.valor_total AS FLOAT64)) as total_facturado,
  SUM(CASE WHEN f.pago_confirmado = 'true' THEN SAFE_CAST(f.valor_total AS FLOAT64) ELSE 0 END) as total_pagado,
  SUM(CASE WHEN f.pago_confirmado != 'true' THEN SAFE_CAST(f.valor_total AS FLOAT64) ELSE 0 END) as total_pendiente,
  MIN(f.fecha_factura) as primera_factura,
  MAX(f.fecha_factura) as ultima_factura
FROM {T}.facturas` f
JOIN {T}.contratos_electronicos` c ON f.id_contrato = c.id_contrato
GROUP BY f.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato
""", "Flujo de facturacion y pagos por contrato")

# Compromisos presupuestales
create_view("v_gasto_compromisos", f"""
SELECT
  cp.id_contrato,
  c.nombre_entidad,
  cp.tipo_de_compromiso,
  COUNT(*) as num_items,
  SUM(SAFE_CAST(cp.valor_item AS FLOAT64)) as valor_comprometido,
  SUM(SAFE_CAST(cp.balance_compromiso AS FLOAT64)) as balance,
  SUM(SAFE_CAST(cp.valor_a_liberar AS FLOAT64)) as valor_a_liberar
FROM {T}.compromisos_presupuestales` cp
JOIN {T}.contratos_electronicos` c ON cp.id_contrato = c.id_contrato
GROUP BY cp.id_contrato, c.nombre_entidad, cp.tipo_de_compromiso
""", "Balance de compromisos presupuestales por contrato")

# ═══════════════════════════════════════════════════════════════════════════
#  MCP 3: INTELIGENCIA DE MERCADO VIEWS
# ═══════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("MCP 3: MERCADO")
print("=" * 60)

# Perfil de proveedor (historial completo)
create_view("v_mercado_perfil_proveedor", f"""
SELECT
  documento_proveedor,
  proveedor_adjudicado as nombre,
  COUNT(*) as total_contratos,
  SUM(valor_del_contrato) as valor_total,
  AVG(valor_del_contrato) as valor_promedio,
  MIN(fecha_de_firma) as primer_contrato,
  MAX(fecha_de_firma) as ultimo_contrato,
  COUNT(DISTINCT nombre_entidad) as entidades_distintas,
  COUNT(DISTINCT departamento) as departamentos,
  COUNT(DISTINCT sector) as sectores,
  STRING_AGG(DISTINCT sector, ', ' LIMIT 5) as sectores_principales,
  STRING_AGG(DISTINCT departamento, ', ' LIMIT 5) as departamentos_principales
FROM {T}.contratos_electronicos`
WHERE documento_proveedor IS NOT NULL AND valor_del_contrato > 0
GROUP BY documento_proveedor, proveedor_adjudicado
""", "Perfil completo de cada proveedor")

# Competencia por categoria UNSPSC
create_view("v_mercado_competencia_sector", f"""
SELECT
  codigo_de_categoria_principal as unspsc,
  documento_proveedor,
  proveedor_adjudicado,
  COUNT(*) as contratos_ganados,
  SUM(valor_del_contrato) as valor_total,
  AVG(valor_del_contrato) as valor_promedio,
  COUNT(DISTINCT nombre_entidad) as entidades_cliente,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY codigo_de_categoria_principal), 2) as pct_mercado
FROM {T}.contratos_electronicos`
WHERE codigo_de_categoria_principal IS NOT NULL
  AND documento_proveedor IS NOT NULL
  AND valor_del_contrato > 0
GROUP BY codigo_de_categoria_principal, documento_proveedor, proveedor_adjudicado
""", "Top proveedores por categoria UNSPSC con % de mercado")

# Tendencia por sector
create_view("v_mercado_tendencia_sector", f"""
SELECT
  codigo_de_categoria_principal as unspsc,
  sector,
  FORMAT_TIMESTAMP('%Y-Q', fecha_de_firma) as trimestre,
  EXTRACT(YEAR FROM fecha_de_firma) as anio,
  COUNT(*) as num_procesos,
  SUM(valor_del_contrato) as valor_total,
  COUNT(DISTINCT documento_proveedor) as proveedores_activos,
  COUNT(DISTINCT nombre_entidad) as entidades_comprando
FROM {T}.contratos_electronicos`
WHERE fecha_de_firma IS NOT NULL AND valor_del_contrato > 0
GROUP BY unspsc, sector, trimestre, anio
""", "Tendencia de contratacion por sector y trimestre")

# Entidades objetivo por sector
create_view("v_mercado_entidades_objetivo", f"""
SELECT
  codigo_de_categoria_principal as unspsc,
  nombre_entidad,
  departamento,
  COUNT(*) as num_contratos,
  SUM(valor_del_contrato) as valor_total,
  AVG(valor_del_contrato) as valor_promedio,
  STRING_AGG(DISTINCT modalidad_de_contratacion, ', ' LIMIT 3) as modalidades_usadas,
  MIN(fecha_de_firma) as desde,
  MAX(fecha_de_firma) as hasta
FROM {T}.contratos_electronicos`
WHERE codigo_de_categoria_principal IS NOT NULL AND valor_del_contrato > 0
GROUP BY unspsc, nombre_entidad, departamento
HAVING COUNT(*) >= 3
""", "Entidades que mas compran por categoria UNSPSC")

# Tasa de exito proponentes
create_view("v_mercado_tasa_exito", f"""
SELECT
  prop.nit_proveedor,
  prop.proveedor as nombre,
  COUNT(DISTINCT prop.id_procedimiento) as participaciones,
  COUNT(DISTINCT c.id_contrato) as adjudicaciones,
  ROUND(COUNT(DISTINCT c.id_contrato) * 100.0 / NULLIF(COUNT(DISTINCT prop.id_procedimiento), 0), 2) as tasa_exito_pct,
  COALESCE(SUM(c.valor_del_contrato), 0) as valor_ganado
FROM {T}.proponentes_proceso` prop
LEFT JOIN {T}.contratos_electronicos` c
  ON prop.nit_proveedor = c.documento_proveedor
GROUP BY prop.nit_proveedor, prop.proveedor
HAVING COUNT(DISTINCT prop.id_procedimiento) >= 3
""", "Tasa de exito por proveedor: participaciones vs adjudicaciones")

# ═══════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)
views = [t for t in client.list_tables(f"{PROJECT}.{DS}") if t.table_type == "VIEW"]
print(f"Total views creadas: {len(list(views))}")
print("DONE!")
