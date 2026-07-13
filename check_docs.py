from google.cloud import bigquery
c = bigquery.Client(project='odin-v2-495523')

# Check urlproceso in procesos
print("=== URLs en procesos_contratacion ===")
r = list(c.query("""
  SELECT urlproceso 
  FROM `odin-v2-495523.secop.procesos_contratacion` 
  WHERE urlproceso IS NOT NULL 
    AND urlproceso NOT LIKE '%login%'
  LIMIT 5
""").result())
for row in r:
    print(dict(row))

# Check if there's a documents dataset we're missing
print("\n=== Distinct documentos_tipo ===")
r2 = list(c.query("""
  SELECT documentos_tipo, descripcion_documentos_tipo, COUNT(*) as n
  FROM `odin-v2-495523.secop.contratos_electronicos`
  WHERE documentos_tipo IS NOT NULL
  GROUP BY 1,2
  ORDER BY n DESC
  LIMIT 10
""").result())
for row in r2:
    print(dict(row))

# Check specific URL-like fields across ALL columns in contratos
print("\n=== Campos con 'url' o 'http' en contratos ===")
r3 = list(c.query("""
  SELECT * FROM `odin-v2-495523.secop.contratos_electronicos`
  LIMIT 1
""").result())
if r3:
    d = dict(r3[0])
    for k, v in d.items():
        sv = str(v) if v else ""
        if "http" in sv.lower() or "secop" in sv.lower():
            print(f"  {k}: {sv[:120]}")
