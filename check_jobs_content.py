import json

with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()

print(f"File size: {len(raw)} chars")
try:
    data = json.loads(raw)
    print(f"json.loads SUCCESS: {len(data)} items")
    if data:
        print("Sample:", data[0].get("id"), data[0].get("status"))
except Exception as e:
    print("json.loads FAILED:", e)
    # Check first 500 chars and last 500 chars
    print("First 300 chars:", raw[:300])
    print("Last 300 chars:", raw[-300:])

