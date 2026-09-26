
import re, json

app_path = r'D:\Highlight_Video_Studio\web\app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

target = "video_path, audio_path, title, duration = download_video_and_audio(url, job_id, DOWNLOADS_DIR, TEMP_DIR)"
replacement = "dl_res = download_video_and_audio(url, job_id, update_status=lambda m: update_msg(m, step=1))\n        video_path = dl_res['video_path']\n        audio_path = dl_res['audio_path']\n        title = dl_res['title']\n        duration = dl_res['duration']"

if target in text:
    text = text.replace(target, replacement)
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("APP_PATCHED_SUCCESS")
else:
    print("APP_TARGET_NOT_FOUND")

# Reset failed job to running or remove so boss can retry cleanly
jobs_path = r'D:\Highlight_Video_Studio\jobs.json'
with open(jobs_path, 'r', encoding='utf-8') as f:
    jobs = json.load(f)

for j in jobs:
    if j.get('status') == 'error':
        print(f"Error job found: {j.get('id')}")

# Restart python backend
import os
os.system('taskkill /F /IM pythonw.exe 2>nul')
os.system('powershell -Command "Start-Process pythonw -ArgumentList \'D:\\Highlight_Video_Studio\\web\\app.py\' -WorkingDirectory \'D:\\Highlight_Video_Studio\'"')
print("RESTARTED_BACKEND")
