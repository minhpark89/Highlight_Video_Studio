
import re, json
from pathlib import Path

# 1. Fix app.py
app_path = r'D:\Highlight_Video_Studio\webpp.py'
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "video_path, audio_path, title, duration = download_video_and_audio(url, job_id, DOWNLOADS_DIR, TEMP_DIR)"
replacement = "dl_res = download_video_and_audio(url, job_id, update_status=lambda m: update_msg(m, step=1))
        video_path = dl_res['video_path']
        audio_path = dl_res['audio_path']
        title = dl_res['title']
        duration = dl_res['duration']"

if target in content:
    content = content.replace(target, replacement)
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIX_APP: SUCCESS")
else:
    print("FIX_APP: ALREADY_OR_NOT_FOUND")

# 2. Check jobs.json and reset error job if needed
jobs_path = r'D:\Highlight_Video_Studio\jobs.json'
with open(jobs_path, 'r', encoding='utf-8') as f:
    jobs = json.load(f)

for j in jobs:
    if j.get("id") == "job_1790092043_f002eb":
        print(f"FOUND JOB: {j.get('id')} status={j.get('status')}")
