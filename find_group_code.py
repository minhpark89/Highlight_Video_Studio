from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where groups are managed in app.py
lines = text.splitlines()
for idx, l in enumerate(lines):
    if "api_save_group" in l or "api_list_groups" in l or "page_groups.json" in l or "add_or_update_group" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-2), min(len(lines), idx+20)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
