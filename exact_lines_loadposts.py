from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

# Search for "async function loadPostsTable()"
start_idx = -1
for idx, l in enumerate(lines):
    if "async function loadPostsTable()" in l:
        start_idx = idx
        break

print(f"loadPostsTable starts at line {start_idx+1}")
for i in range(start_idx, min(len(lines), start_idx + 60)):
    print(f"{i+1}: {repr(lines[i])}")
