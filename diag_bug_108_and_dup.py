import json
from pathlib import Path

# 1. Check posted_clips.json
p_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p_data = json.loads(p_file.read_text(encoding="utf-8")) if p_file.exists() else []
print("posted_clips.json length on disk:", len(p_data))

# 2. Check page_groups.json
g_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(g_file.read_text(encoding="utf-8")) if g_file.exists() else []
print(f"page_groups.json count on disk: {len(groups)}")
for g in groups:
    print(f"  ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}")

# 3. Check app.py POST /api/groups
app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
print("\napp.py POST /api/groups:\n", app_py[pos:pos+500])
