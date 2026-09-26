from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

for line in text.splitlines():
    if "/api/posts" in line or "/api/queue" in line:
        print(line)
