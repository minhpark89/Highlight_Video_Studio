import urllib.request
import json
import re

print("=== 1. VERIFY JOBS.JSON & API /api/jobs ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    jobs = json.loads(r.read().decode('utf-8'))
    print("API /api/jobs returned:", len(jobs), "jobs")
except Exception as e:
    print("API /api/jobs error:", e)

print("\n=== 2. UPDATE TEMPLATES (FIX BLOG LABEL) ===")
for p in [r'D:\Highlight_Video_Studio\web\templates\index.html', r'D:\Highlight_Video_Studio\web\index.html']:
    try:
        with open(p, 'r', encoding='utf-8') as f:
            c = f.read()
        c = c.replace('Đính kèm link Blog bài viết (boostnews.danhngon.pro)', 'Đính kèm link bài viết Blog Website')
        c = c.replace('placeholder="https://boostnews.danhngon.pro"', 'placeholder="https://yourblogdomain.com"')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Updated blog label in {p}")
    except Exception as e:
        print(f"Error updating {p}: {e}")

