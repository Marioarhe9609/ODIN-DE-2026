"""Check fields available for the 5 new red flags"""
from google.cloud import bigquery
PROJECT = "odin-v2-495523"
DS = "secop"
client = bigquery.Client(project=PROJECT)
T = f"`{PROJECT}.{DS}"

print("=" * 70)
print("BANDERA 1: Adiciones acumuladas por contrato")
print("=" * 70)
q = f"SELECT * FROM {T}.adiciones` LIMIT 3"
for r in client.query(q).result():
    print(dict(r))
    break
print("\\nCampos:", [k for k in dict(r).keys() if not k.startswith("_")])

print("\\n" + "=" * 70)
print("BANDERA 2: Contratacion directa - campos tipo_de_contrato")
print("=" * 70)
q2 = f"""SELECT DISTINCT tipo_de_contrato, COUNT(*) c 
FROM {T}.contratos_electronicos` 
WHERE modalidad_de_contratacion LIKE '%irecta%'
GROUP BY tipo_de_contrato ORDER BY c DESC LIMIT 15"""
for r in client.query(q2).result():
    print(f"  {r.tipo_de_contrato:60s} {r.c:>10,}")

print("\\n" + "=" * 70)
print("BANDERA 3: Consulta publica - campos en procesos")
print("=" * 70)
q3 = f"""SELECT DISTINCT estado_del_procedimiento, COUNT(*) c
FROM {T}.procesos_contratacion`
GROUP BY estado_del_procedimiento ORDER BY c DESC LIMIT 15"""
for r in client.query(q3).result():
    print(f"  {r.estado_del_procedimiento:50s} {r.c:>10,}")

print("\\n" + "=" * 70)
print("BANDERA 4: Mismos postulantes - campos en proponentes")
print("=" * 70)
q4 = f"SELECT * FROM {T}.proponentes_proceso` LIMIT 1"
for r in client.query(q4).result():
    print("Campos:", [k for k in dict(r).keys() if not k.startswith("_")])
    print(dict(r))

print("\\n" + "=" * 70)
print("BANDERA 5: Coincidencias representante/tel/correo/direccion")
print("=" * 70)
# Check contratos for these fields
q5 = f"""SELECT column_name FROM `{PROJECT}.{DS}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'contratos_electronicos'
AND (column_name LIKE '%repres%' OR column_name LIKE '%telefono%' 
     OR column_name LIKE '%celular%' OR column_name LIKE '%correo%' 
     OR column_name LIKE '%direccion%' OR column_name LIKE '%email%'
     OR column_name LIKE '%contact%' OR column_name LIKE '%legal%')"""
print("En contratos_electronicos:")
for r in client.query(q5).result():
    print(f"  {r.column_name}")

# Check grupos_proveedores for these fields
q6 = f"""SELECT column_name FROM `{PROJECT}.{DS}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'grupos_proveedores'
AND (column_name LIKE '%repres%' OR column_name LIKE '%telefono%' 
     OR column_name LIKE '%celular%' OR column_name LIKE '%correo%' 
     OR column_name LIKE '%direccion%' OR column_name LIKE '%email%'
     OR column_name LIKE '%contact%' OR column_name LIKE '%legal%')"""
print("\\nEn grupos_proveedores:")
for r in client.query(q6).result():
    print(f"  {r.column_name}")

# Check proponentes
q7 = f"""SELECT column_name FROM `{PROJECT}.{DS}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'proponentes_proceso'
AND (column_name LIKE '%repres%' OR column_name LIKE '%telefono%' 
     OR column_name LIKE '%celular%' OR column_name LIKE '%correo%' 
     OR column_name LIKE '%direccion%' OR column_name LIKE '%email%'
     OR column_name LIKE '%contact%' OR column_name LIKE '%legal%')"""
print("\\nEn proponentes_proceso:")
for r in client.query(q7).result():
    print(f"  {r.column_name}")

# Check ALL tables for these fields
q8 = f"""SELECT table_name, column_name FROM `{PROJECT}.{DS}.INFORMATION_SCHEMA.COLUMNS`
WHERE (column_name LIKE '%repres%' OR column_name LIKE '%telefono%' 
     OR column_name LIKE '%celular%' OR column_name LIKE '%correo%' 
     OR column_name LIKE '%direccion%' OR column_name LIKE '%email%'
     OR column_name LIKE '%contact%' OR column_name LIKE '%legal%')
ORDER BY table_name"""
print("\\nTODAS las tablas con estos campos:")
for r in client.query(q8).result():
    print(f"  {r.table_name:40s} {r.column_name}")

# Sample grupos_proveedores for address/contact fields
print("\\n" + "=" * 70)
print("MUESTRA: grupos_proveedores (direccion, contacto)")
print("=" * 70)
q9 = f"""SELECT direcci_n_grupo, tel_fono_grupo, correo_grupo
FROM {T}.grupos_proveedores`
WHERE direcci_n_grupo IS NOT NULL AND direcci_n_grupo != ''
LIMIT 5"""
for r in client.query(q9).result():
    print(dict(r))
