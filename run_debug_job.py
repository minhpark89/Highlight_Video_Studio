import json, os, subprocess

print("=== Checking jobs.json ===")
with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
    jobs = json.load(f)

print(f"Total jobs: {len(jobs)}")
for j in jobs[-5:]:
    print("ID:", j.get("id"), "Status:", j.get("status"), "URL:", j.get("youtube_url"), "Error:", j.get("error"))

print("\n=== Checking web/app.py around run_job or create_job ===")
with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

idx = app_text.find("def create_job")
if idx != -1:
    print(app_text[idx:idx+2000])

