from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's search where groups are handled
pos = text.find('api_save_group')
if pos == -1: pos = text.find('groups')
lines = text.splitlines()
for idx, l in enumerate(lines):
    if '/api/groups' in l or 'api_save_group' in l or 'page_groups' in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-1), min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
