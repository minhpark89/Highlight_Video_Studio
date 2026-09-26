from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where @app.route("/") is in app.py
lines = app_py.splitlines()
for idx, line in enumerate(lines):
    if '@app.route("/")' in line or '@app.route(\'/\')' in line:
        print(f"Line {idx+1}: {line}")
        for j in range(idx, min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
