import json
import urllib.request

# 1. Check jobs.json loading
with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
    text = f.read()

try:
    j = json.loads(text)
    print("Direct json.loads SUCCESS! Total jobs:", len(j))
except Exception as e:
    print("Direct json.loads FAILED:", e)

# 2. Check /api/jobs
try:
    resp = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    data = json.loads(resp.read().decode('utf-8'))
    print("API /api/jobs returned:", len(data))
except Exception as e:
    print("API /api/jobs error:", e)

# 3. Check tokens and pages
try:
    resp_t = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens")
    t_data = json.loads(resp_t.read().decode('utf-8'))
    print("API /api/tokens returned:", len(t_data.get('tokens', [])))
except Exception as e:
    print("API /api/tokens error:", e)

try:
    resp_p = urllib.request.urlopen("http://127.0.0.1:5080/api/pages")
    p_data = json.loads(resp_p.read().decode('utf-8'))
    print("API /api/pages returned:", len(p_data.get('pages', [])))
except Exception as e:
    print("API /api/pages error:", e)

