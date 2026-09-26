import json

print("=== 1. CHECK APP.PY load_jobs ===")
with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

import re
m = re.search(r'def load_jobs\(\):.*?(?=def |\Z)', app_code, re.DOTALL)
if m:
    print(m.group(0)[:500])

print("\n=== 2. CHECK api_add_token IN APP.PY ===")
m2 = re.search(r'def api_add_token\(\):.*?(?=@app\.route|\Z)', app_code, re.DOTALL)
if m2:
    print(m2.group(0)[:800])

