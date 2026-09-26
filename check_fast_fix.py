import json

print("=== CHECK JOBS LOADING IN APP.PY ===")
with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    code = f.read()

import re
m = re.search(r'def load_jobs\(\):.*?(?=def |\Z)', code, re.DOTALL)
if m:
    print(m.group(0))

with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
    raw = f.read()
print("jobs.json length:", len(raw))
try:
    data = json.loads(raw)
    print("Direct json.loads SUCCESS! Items:", len(data))
except Exception as e:
    print("json.loads FAILED:", e)

