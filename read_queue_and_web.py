import urllib.request
import json
import re

print("=== 1. TEST /api/jobs FROM PORT 5080 ===")
try:
    req = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    data = json.loads(req.read().decode('utf-8'))
    print("API /api/jobs returned:", len(data), "jobs")
    if data:
        print("Status count:", {s: sum(1 for x in data if x.get('status') == s) for s in set(x.get('status') for x in data)})
except Exception as e:
    print("API /api/jobs error:", e)

print("\n=== 2. CHECK JOBS LOADING FUNCTION IN APP.PY ===")
with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

m = re.search(r'def load_jobs\(\):.*?(?=def |\Z)', app_py, re.DOTALL)
if m:
    print(m.group(0))

print("\n=== 3. CHECK HARCODED DOMAIN BOOSTNEWS IN TEMPLATES ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    tpl = f.read()

matches = re.finditer(r'boostnews\.danhngon\.pro', tpl)
for match in matches:
    idx = match.start()
    print("--- Match at", idx, ":")
    print(tpl[max(0, idx-120):min(len(tpl), idx+180)])

