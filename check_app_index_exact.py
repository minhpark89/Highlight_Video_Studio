from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, line in enumerate(app_py.splitlines()):
    if 'def index()' in line:
        for j in range(max(0, idx-2), min(len(app_py.splitlines()), idx+10)):
            print(f"{j+1}: {app_py.splitlines()[j]}")
