import urllib.request
import json

print("=== CHECKING APIS ===")
for path in ['/api/jobs', '/api/tokens', '/api/pages', '/api/groups', '/api/schedule/rules', '/api/website/config']:
    try:
        url = f'http://127.0.0.1:5080{path}'
        req = urllib.request.urlopen(url, timeout=5)
        raw = req.read().decode('utf-8')
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                print(f"{path}: OK (HTTP {req.status}) - List with {len(data)} items")
            elif isinstance(data, dict):
                keys = list(data.keys())[:5]
                print(f"{path}: OK (HTTP {req.status}) - Dict with keys {keys}")
            else:
                print(f"{path}: OK (HTTP {req.status}) - {type(data)}")
        except Exception as je:
            print(f"{path}: JSON DECODE ERROR: {je} (First 100 chars: {raw[:100]})")
    except Exception as e:
        print(f"{path}: HTTP ERROR: {e}")
