from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where groups are saved in app.py
# Search for page_manager.add_or_update_group or /api/groups
matches = []
for idx, line in enumerate(text.splitlines()):
    if "api/groups" in line or "add_or_update_group" in line or "page_groups.json" in line:
        matches.append((idx+1, line))

print("Occurrences:")
for m in matches:
    print(m)
