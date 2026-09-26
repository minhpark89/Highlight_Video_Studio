from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where /api/groups is defined
pos = app_py.find('@app.route("/api/groups"')
if pos == -1: pos = app_py.find("api_save_group")
if pos == -1: pos = app_py.find("/api/groups")

print(app_py[pos-50:pos+800])
