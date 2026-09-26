import urllib.request
import json
import re

print("=== 1. VERIFY /api/jobs CALL ===")
try:
    resp = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    data = json.loads(resp.read().decode('utf-8'))
    print("API /api/jobs items:", len(data))
    if data:
        print("First job:", data[0].get("id"), data[0].get("status"), data[0].get("step"))
except Exception as e:
    print("API /api/jobs failed:", e)

print("\n=== 2. VERIFY /api/tokens & /api/pages ===")
for ep in ['/api/tokens', '/api/pages', '/api/groups', '/api/schedule/rules']:
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:5080{ep}", timeout=5)
        d = json.loads(r.read().decode('utf-8'))
        print(ep, "-> HTTP", r.status, "keys:", list(d.keys()) if isinstance(d, dict) else len(d))
    except Exception as e:
        print(ep, "failed:", e)

