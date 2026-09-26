import json
import urllib.request
import re

print("=== 1. TEST /api/jobs ===")
try:
    resp = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs", timeout=5)
    data = json.loads(resp.read().decode('utf-8'))
    print("API /api/jobs returned items:", len(data))
    if data:
        print("Sample job status:", data[0].get("id"), data[0].get("status"), data[0].get("video_title"))
except Exception as e:
    print("Error calling /api/jobs:", e)

print("\n=== 2. CHECK BOOSTNEWS HARDCODED TEXT ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'.{0,50}boostnews\.danhngon\.pro.{0,50}', html)
for m in matches:
    print("Found hardcoded:", m.strip())

