import json
from pathlib import Path

# 1. Inspect groups in page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print("=== Current groups in page_groups.json ===")
    for g in groups:
        print(f"ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}")

# 2. Check why saving edit group creates a NEW group instead of overwriting!
# Let's inspect web/app.py route /api/groups
app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
print("\n=== POST /api/groups in app.py ===")
print(app_py[pos:pos+700])
