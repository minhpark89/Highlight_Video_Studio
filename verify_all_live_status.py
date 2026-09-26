import requests
import json
from pathlib import Path

# 1. Check posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
print(f"posted_clips.json on disk: {len(posted)} items")

# 2. Check /api/clips
rc = requests.get("http://127.0.0.1:5080/api/clips")
clips = rc.json()
posted_cnt = len([c for c in clips if c.get("is_posted")])
print(f"Total clips: {len(clips)}, is_posted count: {posted_cnt}")

# 3. Check /api/schedule/rules
rr = requests.get("http://127.0.0.1:5080/api/schedule/rules")
print("Status /api/schedule/rules:", rr.status_code, rr.json())

# 4. Check /api/pages
rp = requests.get("http://127.0.0.1:5080/api/pages")
print("Status /api/pages:", rp.status_code, len(rp.json().get("pages", [])))
