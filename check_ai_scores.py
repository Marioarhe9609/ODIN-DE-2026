from agent.bq_client import query

sql = """
SELECT 
  id_del_proceso, 
  nombre_del_procedimiento as name, 
  precio_base as valor,
  modalidad_de_contratacion as modalidad,
  fecha_de_publicacion_del_proceso as publicado,
  CASE 
    WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'inteligencia artificial') > 0 
    THEN 1000 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'inteligencia artificial')
    ELSE 0 
  END AS score 
FROM `odin-v2-495523.secop.procesos_contratacion` 
WHERE id_del_proceso IN (
  'CO1.REQ.10253107', 'CO1.REQ.10331905', 'CO1.REQ.10252610', 
  'CO1.REQ.10227505', 'CO1.REQ.10331179', 'CO1.REQ.10365966', 'CO1.REQ.10256748'
)
ORDER BY score DESC, publicado DESC
"""

rows = query(sql)
for idx, r in enumerate(rows):
    print(f"#{idx+1} | ID: {r['id_del_proceso']} | Score: {r['score']} | Valor: ${float(r['valor']):,.0f} | Mod: {r['modalidad']}\n  Name: {r['name']}\n")
