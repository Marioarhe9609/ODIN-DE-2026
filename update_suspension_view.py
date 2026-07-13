from google.cloud import bigquery
import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

sql_suspension = """
CREATE OR REPLACE VIEW `odin-v2-495523.secop.v_anticorr_suspensiones` AS
SELECT                                                                                  
  s.id_contrato,                                                                        
  c.nombre_entidad,                                                                     
  c.proveedor_adjudicado,                                                               
  c.valor_del_contrato,                                                                 
  COUNT(*) as num_suspensiones,                                                         
  MIN(s.fecha_de_creacion) as primera_suspension,                                       
  MAX(s.fecha_de_creacion) as ultima_suspension,                                        
  STRING_AGG(DISTINCT s.proposito_de_la_modificacion, ' | ' LIMIT 5) as propositos      
FROM `odin-v2-495523.secop.suspensiones_contratos` s                                    
JOIN `odin-v2-495523.secop.contratos_electronicos` c ON s.id_contrato = c.id_contrato   
WHERE s.tipo = 'Suspension'
GROUP BY s.id_contrato, c.nombre_entidad, c.proveedor_adjudicado, c.valor_del_contrato  
HAVING COUNT(*) >= 3
"""

try:
    print("Updating v_anticorr_suspensiones...")
    client.query(sql_suspension).result()
    print("View updated successfully.")
except Exception as e:
    print(f"Error updating v_anticorr_suspensiones: {e}")
