import json
from pathlib import Path

# 1. Inspect page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print("=== Groups in page_groups.json ===")
    for g in groups:
        print(f"ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}")

# 2. Check why saving edit group creates a duplicate instead of updating!
app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, l in enumerate(app_py.splitlines()):
    if "/api/groups" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(app_py.splitlines()), idx+25)):
            print(f"  {j+1}: {app_py.splitlines()[j]}")
