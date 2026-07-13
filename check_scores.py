from agent.bq_client import query

sql = """
SELECT 
  id_del_proceso, 
  SUBSTR(nombre_del_procedimiento, 1, 60) as name, 
  CASE 
    WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'desarrollo de software') > 0 
    THEN 1000 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'desarrollo de software')
    WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'software') > 0 
    THEN 500 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(nombre_del_procedimiento, NFD), r'\\\\pM', '')), 'software')
    ELSE 0 
  END AS score 
FROM `odin-v2-495523.secop.procesos_contratacion` 
WHERE id_del_proceso IN ('CO1.REQ.10332305', 'CO1.REQ.10244371', 'CO1.REQ.10410683', 'CO1.REQ.10253973')
ORDER BY score DESC
"""

rows = query(sql)
for r in rows:
    print(f"ID: {r['id_del_proceso']} | Score: {r['score']} | Name: {r['name']}")
