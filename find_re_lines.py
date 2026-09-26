from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

lines = text.splitlines()
re_lines = [(i+1, l) for i, l in enumerate(lines) if 'import re' in l]
print("Lines with import re:", re_lines)
