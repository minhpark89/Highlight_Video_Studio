import urllib.request
import json

resp = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
jobs = json.loads(resp.read().decode('utf-8'))
print(f"Jobs returned: {len(jobs)}")
if jobs:
    print("Statuses:", {j.get('status') for j in jobs})
    print("Latest 3 jobs:", [(j.get('id'), j.get('status'), j.get('progress'), j.get('step')) for j in jobs[:3]])

# Check tokens
resp_t = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens")
tokens = json.loads(resp_t.read().decode('utf-8'))
print(f"Tokens returned: {len(tokens.get('tokens', []))}")

# Check pages
resp_p = urllib.request.urlopen("http://127.0.0.1:5080/api/pages")
pages = json.loads(resp_p.read().decode('utf-8'))
print(f"Pages returned: {len(pages.get('pages', []))}")

