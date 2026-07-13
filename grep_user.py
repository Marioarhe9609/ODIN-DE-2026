with open("logs_cloudrun.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

user_id = "8797849868"
for idx, line in enumerate(lines):
    if user_id in line:
        print(f"--- Line {idx} ---")
        start = max(0, idx - 2)
        end = min(len(lines), idx + 8)
        for i in range(start, end):
            print(f"{i}: {lines[i].strip()}")
