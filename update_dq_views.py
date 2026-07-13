from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

# 1. v_anticorr_sin_competencia
sql_sin_comp = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_sin_competencia` AS
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
FROM `odin-v2-495523.secop.procesos_contratacion` p    
WHERE p.proveedores_unicos_con_respuesta = 1           
  AND p.modalidad_de_contratacion NOT LIKE '%irecta%'  
  AND p.adjudicado = 'Si'                              
  AND SAFE_CAST(p.precio_base AS FLOAT64) > 1000000
"""

# 2. v_anticorr_sobrecosto
sql_sobrecosto = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_sobrecosto` AS
SELECT                                                                                         
  id_del_proceso,                                                                              
  nombre_del_procedimiento,                                                                    
  nombre_entidad,                                                                              
  modalidad_de_contratacion,                                                                   
  precio_base,                                                                                 
  valor_total_adjudicacion,                                                                    
  ROUND((valor_total_adjudicacion - precio_base) * 100.0 / NULLIF(precio_base, 0), 2) as pct_sobrecosto,  
  nombre_del_proveedor                                                                         
FROM `odin-v2-495523.secop.procesos_contratacion`                                              
WHERE SAFE_CAST(precio_base AS FLOAT64) > 1000000                                                                          
  AND valor_total_adjudicacion > 0                                                             
  AND valor_total_adjudicacion > precio_base * 1.3                                             
  AND adjudicado = 'Si'
"""

# 3. v_anticorr_monopolista
sql_monopolio = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_monopolista` AS
SELECT                                                                                                     
  nombre_entidad,                                                                                          
  documento_proveedor,                                                                                     
  proveedor_adjudicado,                                                                                    
  COUNT(*) as num_contratos,                                                                               
  SUM(valor_del_contrato) as valor_total,                                                                  
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY nombre_entidad), 2) as pct_contratos_entidad,  
  MIN(fecha_de_firma) as primer_contrato,                                                                  
  MAX(fecha_de_firma) as ultimo_contrato                                                                   
FROM `odin-v2-495523.secop.contratos_electronicos`                                                         
WHERE documento_proveedor IS NOT NULL 
  AND nombre_entidad IS NOT NULL
  AND valor_del_contrato > 0
  AND valor_del_contrato < 5000000000000
GROUP BY nombre_entidad, documento_proveedor, proveedor_adjudicado                                         
HAVING COUNT(*) >= 5
"""

# 4. v_anticorr_fraccionamiento
sql_fracc = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_fraccionamiento` AS
SELECT                                                                   
  nombre_entidad,                                                        
  documento_proveedor,                                                   
  proveedor_adjudicado,                                                  
  FORMAT_TIMESTAMP('%Y-%m', SAFE_CAST(fecha_de_firma AS TIMESTAMP)) as mes,                      
  COUNT(*) as num_contratos_minima,                                      
  SUM(valor_del_contrato) as valor_total_sumado,                         
  AVG(valor_del_contrato) as valor_promedio                              
FROM `odin-v2-495523.secop.contratos_electronicos`                       
WHERE modalidad_de_contratacion LIKE '%nima%'                            
  AND documento_proveedor IS NOT NULL                                    
  AND fecha_de_firma IS NOT NULL
  AND valor_del_contrato > 0
  AND valor_del_contrato < 5000000000000
GROUP BY nombre_entidad, documento_proveedor, proveedor_adjudicado, mes  
  HAVING COUNT(*) >= 3
"""

views = {
    "v_anticorr_sin_competencia": sql_sin_comp,
    "v_anticorr_sobrecosto": sql_sobrecosto,
    "v_anticorr_monopolista": sql_monopolio,
    "v_anticorr_fraccionamiento": sql_fracc
}

for name, sql in views.items():
    try:
        print(f"Updating {name}...")
        client.query(sql).result()
        print(f"Successfully updated {name}")
    except Exception as e:
        print(f"Error updating {name}: {e}")

print("All DQ views updated.")
