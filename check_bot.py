from dotenv import load_dotenv
load_dotenv()
import os, requests
t = os.getenv("TELEGRAM_BOT_TOKEN")
r = requests.get(f"https://api.telegram.org/bot{t}/getMe")
d = r.json()["result"]
print(f"Nombre: {d['first_name']}")
print(f"Username: @{d['username']}")
print(f"Link: https://t.me/{d['username']}")
