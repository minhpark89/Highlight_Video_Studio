import urllib.request
import json
import re

print("=== CHECK JOBS API ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print("Jobs count returned by API:", len(jobs))
    if jobs:
        print("Status count:", {s: sum(1 for x in jobs if x.get('status') == s) for s in set(x.get('status') for x in jobs)})
        queued_or_running = [j for j in jobs if j.get('status') in ['queued', 'running']]
        print("Active jobs count:", len(queued_or_running))
        for j in queued_or_running[:3]:
            print(" - Job:", j.get('id'), j.get('status'), j.get('progress'), j.get('step'), j.get('video_title'))
except Exception as e:
    print("Jobs API error:", e)

print("\n=== CHECK BOOSTNEWS HARDCODED TEXT ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's see all places containing boostnews.danhngon.pro
matches = [(m.start(), text[max(0, m.start()-80):min(len(text), m.start()+120)]) for m in re.finditer(r'boostnews\.danhngon\.pro', text)]
for idx, snippet in matches:
    print(f"[{idx}]: {snippet.strip()}\n")

