import json, os, re

base = r"C:\Users\ASUS\.gemini\antigravity\brain\16534b54-0b2f-4ec5-bbc4-7589cf17d05f\.system_generated\steps"

for step in range(333, 346):
    path = os.path.join(base, str(step), "content.md")
    if not os.path.exists(path):
        continue
    raw = open(path, encoding="utf-8").read()
    # Find the JSON object
    start = raw.find("{")
    if start == -1:
        continue
    json_str = raw[start:]
    try:
        data = json.loads(json_str)
    except:
        # Try to find balanced braces
        depth = 0
        end = start
        for i, c in enumerate(json_str):
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            if depth == 0:
                end = i + 1
                break
        try:
            data = json.loads(json_str[:end])
        except Exception as e:
            print(f"Step {step}: PARSE ERROR")
            continue

    name = data.get("name", "?")
    ds_id = data.get("id", "?")
    cols = data.get("columns", [])
    num_cols = len(cols)

    # Get row count from first column's cachedContents
    row_count = "?"
    if cols:
        cached = cols[0].get("cachedContents", {})
        row_count = cached.get("count", cached.get("non_null", "?"))

    try:
        rc = f"{int(row_count):>12,}"
    except:
        rc = f"{'?':>12s}"
    print(f"{ds_id} | {name[:65]:65s} | {rc} rows | {num_cols} cols")
