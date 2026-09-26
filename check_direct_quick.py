import urllib.request
import json
import re

print("=== CHECK JOBS API ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    jobs = json.loads(r.read().decode('utf-8'))
    print("API /api/jobs returned:", len(jobs), "jobs")
except Exception as e:
    print("API /api/jobs error:", e)

print("=== CHECK JOBS FILE ===")
try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        file_jobs = json.load(f)
    print("File jobs.json items:", len(file_jobs))
    by_st = {}
    for x in file_jobs:
        by_st[x.get('status')] = by_st.get(x.get('status'), 0) + 1
    print("File jobs status count:", by_st)
except Exception as e:
    print("File jobs.json error:", e)

print("=== CHECK TEMPLATE BLOG TEXT ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    tpl = f.read()

for target in ['boostnews.danhngon.pro', 'Đính kèm link bài viết Blog Website']:
    print(f"Contains '{target}':", target in tpl)

