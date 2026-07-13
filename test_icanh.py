import asyncio
import os
import sys

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
    
    user_id = "test_user_icanh"
    await session_service.create_session(app_name="test_chat", user_id=user_id, session_id=user_id)
    
    query_text = "Hola soy el ICANH puedes generarme un pdf con todoslos contratos que he celebrado por todas las modalidades en 2026"
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
                if event.content and event.content.parts:
                    print(f"\nFinal response received! Parts: {len(event.content.parts)}")
                    for part in event.content.parts:
                        if part.text:
                            # Safely print even with non-ascii characters on Windows cmd
                            sys.stdout.buffer.write(part.text.encode('utf-8'))
                            sys.stdout.flush()
                else:
                    print("\nFinal response received but content/parts is None or empty!")
            elif hasattr(event, 'content') and event.content:
                 for part in event.content.parts:
                     if part.function_call:
                         print(f"\n[Llamando herramienta: {part.function_call.name} con argumentos {part.function_call.args}]")
    except Exception as e:
        print(f"\nERROR: {e}")
    print("\n" + "-" * 60)

if __name__ == "__main__":
    asyncio.run(test())
