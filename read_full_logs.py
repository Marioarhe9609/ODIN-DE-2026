import subprocess

def read_logs():
    cmd = "gcloud run services logs read odin-bot --project=odin-v2-495523 --region=us-central1 --limit=150"
    print("Fetching Cloud Run logs...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    lines = res.stdout.split("\n")
    # Print the last 60 lines
    for l in lines[-60:]:
        print(l)

if __name__ == "__main__":
    read_logs()
