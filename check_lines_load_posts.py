from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

for i in range(5070, min(len(lines), 5150)):
    print(f"{i+1}: {lines[i]}")
