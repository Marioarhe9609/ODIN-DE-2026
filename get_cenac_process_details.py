import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def get_details():
    sql = """
    SELECT 
      id_del_proceso,
      nombre_del_procedimiento AS objeto,
      nombre_entidad AS entidad,
      modalidad_de_contratacion AS modalidad,
      estado_del_procedimiento AS estado,
      precio_base AS valor,
      fecha_de_publicacion_del_proceso AS publicado,
      codigo_principal_de_categoria AS unspsc,
      urlproceso AS url
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE nombre_entidad = 'CENAC AVIACION' 
      AND LOWER(nombre_del_procedimiento) LIKE '%red lan%'
    """
    print("Running query...")
    for r in client.query(sql).result():
        print(dict(r))

if __name__ == "__main__":
    get_details()
