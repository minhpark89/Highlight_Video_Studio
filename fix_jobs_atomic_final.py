import json
import os
import re

print("=== FIX JOBS.JSON CORRUPTION & PREVENT RECURRENCE ===")
# 1. Clean jobs.json
JOBS_FILE = r'D:\Highlight_Video_Studio\jobs.json'
with open(JOBS_FILE, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

decoder = json.JSONDecoder()
try:
    obj, _ = decoder.raw_decode(text.strip())
    # Clean any invalid newlines in strings
    cleaned_text = json.dumps(obj, ensure_ascii=False, indent=2)
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)
    print(f"Cleaned jobs.json successfully! Count: {len(obj)}")
except Exception as e:
    print("Error cleaning jobs.json:", e)

# 2. Update pipeline.py to use retry & atomic write with lock
PIPE_PATH = r'D:\Highlight_Video_Studio\src\pipeline.py'
with open(PIPE_PATH, 'r', encoding='utf-8') as f:
    pipe_text = f.read()

# Check if pipeline has save_jobs or update_job
print("Pipeline length:", len(pipe_text))

