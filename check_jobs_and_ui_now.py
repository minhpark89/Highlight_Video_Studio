import urllib.request
import json
import re

print("=== 1. VERIFY /api/jobs FROM SERVER ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    jobs = json.loads(r.read().decode('utf-8'))
    print("API /api/jobs returns:", len(jobs), "jobs")
except Exception as e:
    print("API /api/jobs error:", e)

print("\n=== 2. VERIFY JOBS.JSON ON DISK ===")
try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        file_jobs = json.load(f)
    print("jobs.json on disk has:", len(file_jobs), "jobs")
    active = [j for j in file_jobs if j.get('status') in ['queued', 'running', 'processing']]
    print("Active jobs count:", len(active))
except Exception as e:
    print("jobs.json on disk error:", e)

print("\n=== 3. VERIFY TOKENS & PAGES API ===")
try:
    r_tok = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens", timeout=5)
    tokens = json.loads(r_tok.read().decode('utf-8')).get('tokens', [])
    print("Tokens API count:", len(tokens))

    r_pg = urllib.request.urlopen("http://127.0.0.1:5080/api/pages", timeout=5)
    pages = json.loads(r_pg.read().decode('utf-8')).get('pages', [])
    print("Pages API count:", len(pages))
except Exception as e:
    print("Tokens/Pages API error:", e)

print("\n=== 4. CHECK TEMPLATE BLOG TEXT ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Contains 'boostnews.danhngon.pro':", "boostnews.danhngon.pro" in text)
print("Contains 'Đính kèm link bài viết Blog Website':", "Đính kèm link bài viết Blog Website" in text)

