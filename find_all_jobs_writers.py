import re
import os

print("=== CHECK WRITERS OF JOBS.JSON ===")
for root, dirs, files in os.walk(r'D:\Highlight_Video_Studio'):
    if any(x in root for x in ['.git', '__pycache__', 'venv', 'node_modules', 'downloads', 'temp', 'output']):
        continue
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='replace') as pyf:
                    c = pyf.read()
                if 'jobs.json' in c or 'JOBS_FILE' in c:
                    matches = [line.strip() for line in c.splitlines() if 'open(' in line and ('jobs' in line or 'JOBS' in line)]
                    if matches:
                        print(f"File {p}:")
                        for m in matches:
                            print(f"  {m}")
            except Exception as e:
                pass

