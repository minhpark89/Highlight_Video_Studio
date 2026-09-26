import json
from pathlib import Path

# 1. Check posted_clips.json
p_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p_data = json.loads(p_file.read_text(encoding="utf-8")) if p_file.exists() else []
print("posted_clips.json len:", len(p_data))

# 2. Check jobs.json clips
j_file = Path(r"D:\Highlight_Video_Studio\jobs.json")
jobs = json.loads(j_file.read_text(encoding="utf-8")) if j_file.exists() else []
posted_in_jobs = 0
for j in jobs:
    for c in j.get("clips", []):
        if c.get("is_posted"):
            posted_in_jobs += 1
print(f"Jobs count: {len(jobs)}, clips marked is_posted in jobs.json: {posted_in_jobs}")

# 3. Check /api/clips response
import requests
try:
    r = requests.get("http://127.0.0.1:5080/api/clips")
    clips = r.json()
    p_cnt = len([c for c in clips if c.get("is_posted")])
    print(f"/api/clips returns total: {len(clips)}, is_posted count: {p_cnt}")
except Exception as e:
    print("Error calling /api/clips:", e)
