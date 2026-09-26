from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where render_template or send_from_directory is called
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "index.html" in l or "render_template" in l or "def index" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-2), min(len(lines), idx+10)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
