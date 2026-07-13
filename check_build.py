import subprocess, sys
# Get latest build ID
r1 = subprocess.run(
    ["cmd", "/c", "gcloud builds list --project=odin-v2-495523 --region=us-central1 --limit=1 --format=value(id)"],
    capture_output=True, text=True
)
build_id = r1.stdout.strip()
if not build_id:
    print("No build found. Trying global region...")
    r1 = subprocess.run(
        ["cmd", "/c", "gcloud builds list --project=odin-v2-495523 --limit=1 --format=value(id)"],
        capture_output=True, text=True
    )
    build_id = r1.stdout.strip()

if build_id:
    print(f"Build ID: {build_id}")
    r2 = subprocess.run(
        ["cmd", "/c", f"gcloud builds log {build_id} --project=odin-v2-495523 --region=us-central1"],
        capture_output=True, text=True
    )
    # Show last 50 lines
    lines = (r2.stdout + r2.stderr).strip().split("\n")
    for line in lines[-50:]:
        print(line)
else:
    print("No builds found. Checking Cloud Build logs via streaming...")
    r3 = subprocess.run(
        ["cmd", "/c", "gcloud run services describe odin-bot --region=us-central1 --project=odin-v2-495523 2>&1"],
        capture_output=True, text=True
    )
    print(r3.stdout + r3.stderr)
