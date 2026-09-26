from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where groups are managed in app.py
lines = text.splitlines()
matches = [i for i, l in enumerate(lines) if "api_save_group" in l or "api_list_groups" in l or "page_groups.json" in l]
print("Group matches:", matches)
for m in matches:
    print(f"--- Line {m+1} ---")
    for j in range(max(0, m-2), min(len(lines), m+20)):
        print(f"  {j+1}: {lines[j]}")
