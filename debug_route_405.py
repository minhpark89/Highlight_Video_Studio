from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = text.splitlines()

for i in range(1200, 1245):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}")
