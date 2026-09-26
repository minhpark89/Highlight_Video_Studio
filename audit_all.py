import urllib.request
import json
import re

print("=== 1. CHECK API JOBS ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print("Jobs count returned by API:", len(jobs))
    if jobs:
        print("Status count:", {s: sum(1 for x in jobs if x.get('status') == s) for s in set(x.get('status') for x in jobs)})
        print("Sample active jobs:", [(j.get('id'), j.get('status'), j.get('progress'), j.get('progress_msg')) for j in jobs if j.get('status') in ['queued', 'running']][:3])
except Exception as e:
    print("Jobs error:", e)

print("\n=== 2. CHECK BOOSTNEWS OCCURRENCES IN TEMPLATES ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded boostnews label
# "Đính kèm link Blog bài viết (boostnews.danhngon.pro)" -> "Đính kèm link bài viết Blog Website"
# placeholder="https://boostnews.danhngon.pro" -> placeholder="https://yourblogdomain.com"
matches = re.findall(r'.{0,50}boostnews\.danhngon\.pro.{0,50}', text)
for m in matches:
    print("Match:", m.strip())

