from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, line in enumerate(app_py.splitlines()):
    if 'render_template' in line or 'send_from_directory' in line or 'index.html' in line:
        print(f"Line {idx+1}: {line}")
