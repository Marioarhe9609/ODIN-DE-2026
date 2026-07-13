import subprocess
import json

args = [
    "gcloud.cmd", "logging", "read",
    "resource.type=cloud_run_revision AND resource.labels.service_name=odin-bot",
    "--limit=100",
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
        print(f"Retrieved {len(logs)} logs:")
        for log in reversed(logs):
            msg = log.get("textPayload") or log.get("jsonPayload", {}).get("message")
            if msg:
                print(msg.strip())
    except Exception as e:
        print("Error parsing json:")
        print(e)
        print("Raw output first 200 chars:")
        print(res.stdout[:200])
