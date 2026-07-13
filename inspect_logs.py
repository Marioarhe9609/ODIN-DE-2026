import subprocess
import json

args = [
    "gcloud.cmd", "logging", "read",
    "resource.type=cloud_run_revision AND resource.labels.service_name=odin-bot",
    "--limit=350",
    "--project=odin-v2-495523",
    "--format=json"
]

res = subprocess.run(args, capture_output=True, text=True, shell=True)
if res.returncode != 0:
    print("Error running gcloud:")
    print(res.stderr)
else:
    try:
        logs = json.loads(res.stdout)
        print(f"Retrieved {len(logs)} logs.")
        with open("logs_cloudrun.txt", "w", encoding="utf-8") as f:
            for log in reversed(logs):
                msg = log.get("textPayload") or log.get("jsonPayload", {}).get("message")
                if msg:
                    f.write(msg.strip() + "\n")
        print("Written logs to logs_cloudrun.txt")
    except Exception as e:
        print("Error parsing json:")
        print(e)
