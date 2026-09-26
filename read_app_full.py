with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    code = f.read()

import re
# check all endpoints related to jobs, tokens, pages, groups, schedule
endpoints = re.findall(r'@app\.route\([^)]+\)\s+def\s+\w+\([^)]*\):', code)
print("Endpoints found:", len(endpoints))
for ep in endpoints:
    print(ep)

