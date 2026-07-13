import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from google import genai
from google.genai import types

def test_grounding():
    print("Testing Gemini with Google Search Grounding for requirements...")
    # Initialize genai client
    client = genai.Client()
    
    prompt = """
    Analiza el proceso de contratación pública colombiana en SECOP II con las siguientes referencias:
    - ID del Proceso: CO1.REQ.10336146
    - Referencia del Proceso: IPRIV-PS-026-2026
    - Entidad: Empresa de Desarrollo Urbano y Rural de Segovia / Municipio de Uramita
    - Objeto: Desarrollo integral de los procesos de gestión documental.

    Utilizando la búsqueda de Google, encuentra y extrae un resumen estructurado con:
    1. Requisitos de Experiencia Habilitante (Códigos UNSPSC exigidos, valor mínimo del contrato en pesos colombianos, número de contratos previos).
    2. Requisitos Financieros (Indicadores exigidos de Liquidez, Endeudamiento y Razón de Cobertura de Intereses, si están definidos).
    3. Requisitos Técnicos y Perfiles de Personal clave exigidos en los pliegos o términos de referencia.

    Si no encuentras el pliego específico en Google, intenta buscar información del proyecto de Regalías BPIN 202605820001 o similares para dar un perfil preliminar.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                # Enable Google Search grounding
                tools=[{"google_search": {}}],
                temperature=0.2
            )
        )
        print("\nGemini Response:")
        print(response.text)
        
        # Check grounding metadata
        if response.candidates and response.candidates[0].grounding_metadata:
            print("\nGrounding Sources:")
            metadata = response.candidates[0].grounding_metadata
            for idx, chunk in enumerate(metadata.grounding_chunks or []):
                web = chunk.web
                if web:
                    print(f"  [{idx+1}] {web.title}: {web.uri}")
    except Exception as e:
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    test_grounding()
