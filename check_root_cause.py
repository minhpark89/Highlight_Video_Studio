import json
import urllib.request
import re

print("=== 1. CHECK SAVE_JOBS IN APP.PY ===")
with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

m = re.search(r'def save_jobs\([^)]*\):.*?(?=def |\Z)', app_text, re.DOTALL)
if m:
    print(m.group(0))

m_load = re.search(r'def load_jobs\([^)]*\):.*?(?=def |\Z)', app_text, re.DOTALL)
if m_load:
    print(m_load.group(0))

print("=== 2. CHECK HOW PIPELINE UPDATES JOBS ===")
with open(r'D:\Highlight_Video_Studio\src\pipeline.py', 'r', encoding='utf-8') as f:
    pipe_text = f.read()

m_pipe_save = re.findall(r'def (?:save_jobs|update_job_status|load_jobs)[^:]*:', pipe_text)
print("Pipeline job functions:", m_pipe_save)

