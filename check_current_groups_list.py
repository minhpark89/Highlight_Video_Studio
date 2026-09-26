import json
from pathlib import Path

# 1. Inspect page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print("=== Current groups in page_groups.json ===")
    for g in groups:
        print(f"ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}")
