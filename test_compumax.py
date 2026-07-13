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
os.environ["OTEL_SDK_DISABLED"] = "TRUE"

async def test():
    session_service = InMemorySessionService()
    runner = Runner(agent=odin_agent, app_name="test_compumax", session_service=session_service)
    
    user_id = "test_user_compumax"
    await session_service.create_session(app_name="test_compumax", user_id=user_id, session_id=user_id)
    
    query_text = "me podriaas dar el historial del contratista compumax para el 2025"
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=query_text)]
    )
    
    print(f"Sending: {query_text}")
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=user_id,
            new_message=user_content
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        print("Agent Response:")
                        print(part.text)
            elif hasattr(event, 'content') and event.content:
                 for part in event.content.parts:
                     if part.function_call:
                         print(f"Tool call: {part.function_call.name}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test())
