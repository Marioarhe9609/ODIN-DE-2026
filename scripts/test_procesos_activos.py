import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from agent.tools_mercado import procesos_activos

try:
    print("Running procesos_activos locally...")
    res = procesos_activos(sector="desarrollo de software", top=5)
    print("\nResult:")
    print(res)
except Exception as e:
    import traceback
    print(f"Error executing processes_activos: {e}")
    traceback.print_exc()
