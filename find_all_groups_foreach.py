from pathlib import Path
import re

for p in [Path(r"D:\Highlight_Video_Studio\web\templates\index.html"), Path(r"D:\Highlight_Video_Studio\web\index.html")]:
    if p.exists():
        text = p.read_text(encoding="utf-8")
        matches = [m.start() for m in re.finditer(r'groups\.forEach', text)]
        print(f"File {p.name}: {len(matches)} matches for groups.forEach")
        for m in matches:
            print(text[m-50:m+100])
            print("---")
