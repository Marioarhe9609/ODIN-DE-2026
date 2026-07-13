import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def search_cenac():
    sql = """
    SELECT 
      id_del_proceso,
      nombre_del_procedimiento AS objeto,
      nombre_entidad AS entidad,
      modalidad_de_contratacion AS modalidad,
      estado_del_procedimiento AS estado,
      precio_base,
      fecha_de_publicacion_del_proceso AS publicado,
      codigo_principal_de_categoria AS unspsc,
      urlproceso AS url
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE (
        REGEXP_CONTAINS(LOWER(nombre_entidad), 'cenac|icanh|defensa|ejercito')
      )
      AND fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) AS TIMESTAMP)
    ORDER BY fecha_de_publicacion_del_proceso DESC
    LIMIT 50
    """
    print("Running query...")
    rows = list(client.query(sql).result())
    print(f"Found {len(rows)} recent/active processes for CENAC/Defense.")
    for idx, r in enumerate(rows):
        print(f"[{idx+1}] Entidad: {r.entidad} | Estado: {r.estado} | Valor: {r.precio_base} | Objeto: {r.objeto[:120]}...")

if __name__ == "__main__":
    search_cenac()
