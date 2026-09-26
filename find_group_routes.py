from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where groups are managed in app.py
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "api_save_group" in l or "api_list_groups" in l or "page_groups.json" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+30)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
