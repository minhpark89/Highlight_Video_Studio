import urllib.request
import json

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    print("API /api/jobs count:", len(json.loads(r.read().decode())))
except Exception as e:
    print("API /api/jobs error:", e)

try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        j = json.load(f)
    print("File jobs.json count:", len(j))
except Exception as e:
    print("File jobs.json error:", e)
