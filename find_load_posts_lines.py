from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html_tmpl.splitlines()

# Search for "function loadPostsTable" or "async function loadPostsTable"
for idx, l in enumerate(lines):
    if "loadPostsTable" in l and "function" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+40)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
