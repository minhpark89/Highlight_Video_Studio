import urllib.request
import json
import re

print("--- 1. CHECK API /api/jobs ---")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print("API /api/jobs count:", len(jobs))
except Exception as e:
    print("API /api/jobs err:", e)

print("\n--- 2. CHECK JOBS.JSON ---")
try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        j = json.load(f)
    print("File jobs.json valid! Count:", len(j))
    queued_or_running = [x for x in j if x.get('status') in ['queued', 'running', 'processing']]
    print("Active jobs count:", len(queued_or_running))
    for x in queued_or_running[:3]:
        print("  -", x.get('id'), x.get('status'), x.get('step'), x.get('progress'))
except Exception as e:
    print("jobs.json err:", e)

print("\n--- 3. CHECK BOOSTNEWS IN INDEX.HTML ---")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.finditer(r'boostnews\.danhngon\.pro', html)
for m in matches:
    idx = m.start()
    print("Found at", idx, ":", repr(html[max(0, idx-50):min(len(html), idx+80)]))

