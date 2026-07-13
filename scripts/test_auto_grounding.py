import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from google import genai
from google.genai import types

def test_auto_grounding(process_id: str, notice_uid: str):
    print(f"Testing dynamic AI extraction for process {process_id}...")
    
    # 1. Fetch details of the process from processes_contratacion to feed Gemini
    from agent.bq_client import query
    sql = f"""
    SELECT nombre_entidad, nombre_del_procedimiento, precio_base, codigo_principal_de_categoria
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE id_del_proceso = '{process_id}' OR urlproceso LIKE '%{notice_uid}%'
    LIMIT 1
    """
    rows = query(sql)
    if not rows:
        print("Process not found in BigQuery processes_contratacion.")
        return
        
    p = rows[0]
    print("Found process in BQ:")
    print(f"  Entidad: {p['nombre_entidad']}")
    print(f"  Objeto: {p['nombre_del_procedimiento']}")
    print(f"  Valor: ${float(p['precio_base']):,.0f}")
    print(f"  UNSPSC: {p['codigo_principal_de_categoria']}")
    
    # 2. Invoke Gemini with Google Search Grounding
    client = genai.Client()
    prompt = f"""
    Actúa como un experto en contratación pública en Colombia.
    Analiza el siguiente proceso activo de SECOP II:
    - Entidad Contratante: {p['nombre_entidad']}
    - ID del Proceso: {process_id}
    - Objeto: {p['nombre_del_procedimiento']}
    - Presupuesto Base: ${float(p['precio_base']):,.0f} COP
    - Categoría UNSPSC: {p['codigo_principal_de_categoria']}

    Utiliza la búsqueda de Google para localizar los pliegos de condiciones o términos de referencia de este contrato (buscando por el ID, objeto o entidad en SECOP II, ColombiaLicita, o portales municipales). 
    Extrae e interpreta de forma clara y concisa los siguientes requisitos:
    1. REQUISITOS DE EXPERIENCIA HABILANTE: Códigos UNSPSC requeridos (ej: 43233001, 81111800), valor mínimo a certificar en pesos (COP) o SMMLV, y número de contratos anteriores.
    2. REQUISITOS FINANCIEROS Y ORGANIZACIONALES: Indicador de Liquidez mínimo, Índice de Endeudamiento máximo y Razón de Cobertura de Intereses.
    3. REQUISITOS TÉCNICOS Y PERFILES DE PERSONAL: Perfiles clave del equipo de trabajo requeridos (ej. Archivistas, Ingenieros de Sistemas, Diseñadores) y certificaciones técnicas necesarias.

    IMPORTANTE: Si los pliegos exactos no están indexados públicamente en la web (debido a publicación ultra-reciente), genera una ESTIMACIÓN TÉCNICA Y FINANCIERA ALTAMENTE REALISTA basada en los estándares del sector público en Colombia para este tipo de objeto y presupuesto de ${float(p['precio_base']):,.0f} COP en el sector de la categoría {p['codigo_principal_de_categoria']}. Demuestra tu conocimiento analizando el RUP típico y los perfiles estándar exigidos por la ley de contratación pública.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2
            )
        )
        print("\n=== AI EXTRACTED REQUIREMENTS ===")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auto_grounding("CO1.REQ.10336146", "CO1.NTC.10197652")
