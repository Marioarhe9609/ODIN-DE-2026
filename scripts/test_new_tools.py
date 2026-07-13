import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from agent.tools_mercado import detectar_contrato_amarrado, extraer_requisitos_proceso

def test():
    print("==================================================")
    print("TESTING NEW MARKET AND TRANSPARENCY TOOLS LOCALLY")
    print("==================================================")
    
    process_id = "CO1.REQ.10336146"
    
    print("\n1. Testing detectar_contrato_amarrado (Semáforo de Transparencia)...")
    res_sem = detectar_contrato_amarrado(process_id)
    print(res_sem)
    
    print("\n2. Testing extraer_requisitos_proceso (Requisitos IA)...")
    res_req = extraer_requisitos_proceso(process_id)
    print(res_req)

if __name__ == "__main__":
    test()
