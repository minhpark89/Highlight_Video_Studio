import urllib.request
import json
import re

print("=== 1. VERIFY API /api/jobs ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print(f"Jobs count from API: {len(jobs)}")
    statuses = {}
    for j in jobs:
        st = j.get('status', 'unknown')
        statuses[st] = statuses.get(st, 0) + 1
    print("Jobs status breakdown:", statuses)
except Exception as e:
    print("Error calling /api/jobs:", e)

print("\n=== 2. VERIFY /api/tokens & /api/pages ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens")
    toks = json.loads(r.read().decode('utf-8'))
    print("Tokens count:", len(toks.get('tokens', [])))
    
    r2 = urllib.request.urlopen("http://127.0.0.1:5080/api/pages")
    pages = json.loads(r2.read().decode('utf-8'))
    print("Pages count:", len(pages.get('pages', [])))
except Exception as e:
    print("Tokens/Pages API error:", e)

print("\n=== 3. VERIFY BLOG TEXT IN TEMPLATES ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    t = f.read()

print("boostnews.danhngon.pro in templates/index.html:", "boostnews.danhngon.pro" in t)
print("Đính kèm link bài viết Blog Website in templates/index.html:", "Đính kèm link bài viết Blog Website" in t)
