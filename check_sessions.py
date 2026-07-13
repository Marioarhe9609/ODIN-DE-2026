from google.adk.sessions import InMemorySessionService
import inspect

service = InMemorySessionService()
print("Methods in InMemorySessionService:")
for name, member in inspect.getmembers(service):
    if not name.startswith("__"):
        print(f" - {name}")
