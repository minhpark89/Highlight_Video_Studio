from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 1550 to 1650 in index.html to see pane-pages structure
lines = html.splitlines()
for i in range(1550, min(len(lines), 1620)):
    print(f"{i+1}: {lines[i]}")
