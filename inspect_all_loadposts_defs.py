from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

for idx, l in enumerate(lines):
    if "async function loadPostsTable" in l or "function loadPostsTable" in l:
        print(f"Def at line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+50)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
