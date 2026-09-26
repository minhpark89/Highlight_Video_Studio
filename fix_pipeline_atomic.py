import re

p_path = r'D:\Highlight_Video_Studio\src\pipeline.py'
with open(p_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect where save_jobs or update_job_status is in pipeline.py
matches = re.findall(r'def (?:load_jobs|save_jobs|update_job_status)\([^)]*\):.*?(?=\ndef |\Z)', text, re.DOTALL)
for m in matches:
    print("Found in pipeline.py:\n", m[:300], "\n---")

