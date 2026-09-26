from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where render_template or send_from_directory is called in app.py
for idx, line in enumerate(app_py.splitlines()):
    if 'index.html' in line or 'def index' in line or 'template' in line.lower():
        print(f"Line {idx+1}: {line}")
