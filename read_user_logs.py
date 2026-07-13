import subprocess

def read_logs():
    cmd = "gcloud run services logs read odin-bot --project=odin-v2-495523 --region=us-central1 --limit=300"
    print("Fetching Cloud Run logs...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    lines = res.stdout.split("\n")
    # Print lines that contain "User 8834503849" or "sendMessage" or "Done" or "Response received"
    for l in lines[-100:]:
        print(l)

if __name__ == "__main__":
    read_logs()
