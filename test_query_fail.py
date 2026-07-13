import asyncio
import os
from agent import odin_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

async def test():
    session_service = InMemorySessionService()
    runner = Runner(agent=odin_agent, app_name="test", session_service=session_service)
    
    user_id = "test_user_v2"
    await session_service.create_session(app_name="test", user_id=user_id, session_id=user_id)
    
    # EXACT query from user that failed
    message = "Dame un informe en pdf con procesos recientes y que están aún recibiendo ofertas"
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=message)]
    )
    
    print(f"Testing message: {message}")
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=user_id,
            new_message=user_content
        ):
            print(f"Event: {type(event).__name__}")
            if event.is_final_response():
                print(f"Final response received! Parts: {len(event.content.parts)}")
                for part in event.content.parts:
                    if part.text:
                        print(f"Text found (length {len(part.text)})")
            elif hasattr(event, 'content') and event.content:
                 for part in event.content.parts:
                     if part.function_call:
                         print(f"Tool call: {part.function_call.name}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test())
