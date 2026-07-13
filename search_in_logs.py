with open("logs_cloudrun.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "buscar_contratos" in line or "User 8797849868" in line or "User 1501141931" in line:
        print(f"--- Line {idx} ---")
        start = max(0, idx - 3)
        end = min(len(lines), idx + 10)
        for i in range(start, end):
            print(f"{i}: {lines[i].strip()}")
