import urllib.request
import json

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    data = json.loads(r.read().decode('utf-8'))
    print("API /api/jobs items:", len(data))
    if data:
        print("First 3:", [(x.get('id'), x.get('status'), x.get('step'), x.get('progress')) for x in data[:3]])
except Exception as e:
    print("API /api/jobs error:", e)

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens", timeout=5)
    data = json.loads(r.read().decode('utf-8'))
    print("API /api/tokens items:", len(data.get('tokens', [])))
except Exception as e:
    print("API /api/tokens error:", e)

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/pages", timeout=5)
    data = json.loads(r.read().decode('utf-8'))
    print("API /api/pages items:", len(data.get('pages', [])))
except Exception as e:
    print("API /api/pages error:", e)
