from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"

client = bigquery.Client()

sql_adiciones = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_adiciones` AS
SELECT                                                                                          
  c.id_contrato,                                                                                
  c.nombre_entidad,                                                                             
  c.proveedor_adjudicado,                                                                       
  c.valor_del_contrato,                                                                         
  COUNT(*) as num_adiciones,                                                                    
  COUNT(CASE WHEN a.tipo LIKE '%alor%' THEN 1 END) as adiciones_valor,                          
  COUNT(CASE WHEN a.tipo LIKE '%lazo%' OR a.tipo LIKE '%iemp%' THEN 1 END) as adiciones_plazo,  
  MIN(a.fecharegistro) as primera_adicion,                                                      
  MAX(a.fecharegistro) as ultima_adicion                                                        
FROM `odin-v2-495523.secop.contratos_electronicos` c                                            
JOIN (
  SELECT id_contrato, DATE(SAFE_CAST(fecharegistro AS TIMESTAMP)) as fecharegistro, tipo
  FROM `odin-v2-495523.secop.adiciones`
  GROUP BY id_contrato, DATE(SAFE_CAST(fecharegistro AS TIMESTAMP)), tipo
) a ON a.id_contrato = c.id_contrato           
GROUP BY c.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato          
HAVING COUNT(*) >= 3
"""

try:
    print("Updating v_anticorr_adiciones...")
    client.query(sql_adiciones).result()
    print("View updated successfully.")
except Exception as e:
    print(f"Error: {e}")
