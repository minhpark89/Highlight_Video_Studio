from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = content.splitlines()

# Search for loadPostsTable
start_idx = -1
for idx, l in enumerate(lines):
    if "async function loadPostsTable()" in l:
        start_idx = idx
        break

print(f"loadPostsTable at line {start_idx+1}")
# print lines 5100 to 5160
for i in range(start_idx, min(len(lines), start_idx + 60)):
    print(f"{i+1}: {lines[i]}")
