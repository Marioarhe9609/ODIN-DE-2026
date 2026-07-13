from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"

client = bigquery.Client()

sql_flujo = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_gasto_flujo_pagos` AS
WITH facturas_unicas AS (
  SELECT 
    id_contrato,
    numero_de_factura,
    MAX(SAFE_CAST(valor_total AS FLOAT64)) as valor_total,
    MIN(fecha_factura) as fecha_factura
  FROM `odin-v2-495523.secop.facturas`
  WHERE estado = 'Pagado'
  GROUP BY id_contrato, numero_de_factura
)
SELECT                                                                                                                
  f.id_contrato,                                                                                                      
  c.nombre_entidad,                                                                                                   
  c.proveedor_adjudicado,                                                                                             
  c.valor_del_contrato,                                                                                               
  COUNT(*) as num_facturas,                                                                                           
  SUM(f.valor_total) as total_facturado,                                                        
  SUM(f.valor_total) as total_pagado,      
  0.0 as total_pendiente,  
  MIN(f.fecha_factura) as primera_factura,                                                                            
  MAX(f.fecha_factura) as ultima_factura                                                                              
FROM facturas_unicas f                                                                                
JOIN `odin-v2-495523.secop.contratos_electronicos` c ON f.id_contrato = c.id_contrato                                 
GROUP BY f.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato
"""

sql_sobre = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_sobrefacturacion` AS
SELECT                                                                                                                      
  c.id_contrato,                                                                                                            
  c.nombre_entidad,                                                                                                         
  c.proveedor_adjudicado,                                                                                                   
  c.valor_del_contrato,                                                                                                     
  COALESCE(f.total_facturado, 0) as total_facturado,                                                                        
  COALESCE(f.num_facturas, 0) as num_facturas,                                                                              
  ROUND((COALESCE(f.total_facturado, 0) - c.valor_del_contrato) * 100.0 / NULLIF(c.valor_del_contrato, 0), 2) as pct_sobre  
FROM `odin-v2-495523.secop.contratos_electronicos` c                                                                        
JOIN (                                                                                                                      
  WITH facturas_unicas AS (
    SELECT id_contrato, numero_de_factura, MAX(SAFE_CAST(valor_total AS FLOAT64)) as valor_total
    FROM `odin-v2-495523.secop.facturas`
    WHERE estado = 'Pagado'
    GROUP BY id_contrato, numero_de_factura
  )
  SELECT id_contrato, SUM(valor_total) as total_facturado, COUNT(*) as num_facturas                                                                                           
  FROM facturas_unicas                                                                                      
  WHERE valor_total IS NOT NULL                                                                                             
  GROUP BY id_contrato                                                                                                      
) f ON c.id_contrato = f.id_contrato                                                                                        
WHERE c.valor_del_contrato > 0                                                                                              
  AND f.total_facturado > c.valor_del_contrato * 1.1
"""

try:
    print("Updating v_gasto_flujo_pagos...")
    client.query(sql_flujo).result()
    print("Updating v_anticorr_sobrefacturacion...")
    client.query(sql_sobre).result()
    print("Views updated successfully.")
except Exception as e:
    print(f"Error: {e}")
