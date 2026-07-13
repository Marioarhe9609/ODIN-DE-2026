import asyncio
import os
import sys

# Add parent path to import agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import odin_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

async def test():
    session_service = InMemorySessionService()
    runner = Runner(agent=odin_agent, app_name="test_chat", session_service=session_service)
    
    user_id = "test_user_espacios"
    await session_service.create_session(app_name="test_chat", user_id=user_id, session_id=user_id)
    
    query_text = "Soy espacios y redes (NIT 830144531), dame 2 procesos que pueda tener mayor probabilidad de que me los gane"
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=query_text)]
    )
    
    print(f"Enviando consulta al agente Odin v2: '{query_text}'\n")
    print("Respuesta de Odin:")
    print("-" * 60)
    
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=user_id,
            new_message=user_content
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        print(part.text, end="", flush=True)
            elif hasattr(event, 'content') and event.content:
                 for part in event.content.parts:
                     if part.function_call:
                         print(f"\n[Llamando herramienta: {part.function_call.name} con argumentos {part.function_call.args}]")
    except Exception as e:
        print(f"\nERROR: {e}")
    print("\n" + "-" * 60)

if __name__ == "__main__":
    asyncio.run(test())
