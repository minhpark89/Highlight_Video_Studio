with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'def (?:load_jobs|save_jobs)\([^)]*\):.*?(?=\ndef |\Z)', text, re.DOTALL)
for m in matches:
    print("Found in app.py:\n", m[:800], "\n" + "="*40)

with open(r'D:\Highlight_Video_Studio\src\pipeline.py', 'r', encoding='utf-8') as f:
    pipe_text = f.read()

pipe_matches = re.findall(r'def (?:load_jobs|save_jobs|update_job_status)\([^)]*\):.*?(?=\ndef |\Z)', pipe_text, re.DOTALL)
for m in pipe_matches:
    print("Found in pipeline.py:\n", m[:800], "\n" + "="*40)
