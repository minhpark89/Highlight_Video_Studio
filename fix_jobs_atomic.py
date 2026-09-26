import json
import time
import os

JOBS_FILE = r'D:\Highlight_Video_Studio\jobs.json'

with open(JOBS_FILE, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Let's decode JSON object array strictly
decoder = json.JSONDecoder()
try:
    obj, idx = decoder.raw_decode(text.strip())
    print(f"Decoded {len(obj)} items from jobs.json. Truncating extra trailing data.")
    # Write back clean JSON
    tmp_file = JOBS_FILE + '.clean'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, JOBS_FILE)
    print("Replaced jobs.json cleanly!")
except Exception as e:
    print("Decode failed:", e)

# Test reload
with open(JOBS_FILE, 'r', encoding='utf-8') as f:
    verify = json.load(f)
print("Verify loaded successfully! Count:", len(verify))
