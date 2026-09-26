import json
from pathlib import Path

# 1. Inspect groups in page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(groups_file.read_text(encoding="utf-8")) if groups_file.exists() else []
print(f"Total groups in page_groups.json: {len(groups)}")
for g in groups:
    print(f"  ID: {g.get('id')} | Name: {g.get('name')} | Times: {g.get('schedule_config', {}).get('times')}")

# 2. Inspect posted_clips.json
p_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p_data = json.loads(p_file.read_text(encoding="utf-8")) if p_file.exists() else []
print(f"\nposted_clips.json count: {len(p_data)}")

# 3. Check /api/clips
import requests
try:
    r = requests.get("http://127.0.0.1:5080/api/clips")
    clips = r.json()
    posted_cnt = len([c for c in clips if c.get("is_posted")])
    print(f"/api/clips count: {len(clips)}, marked is_posted: {posted_cnt}")
except Exception as e:
    print("Error calling /api/clips:", e)
