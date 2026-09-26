from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

# Search for loadPostsTable
for idx, l in enumerate(lines):
    if "async function loadPostsTable" in l or "function loadPostsTable" in l:
        print(f"loadPostsTable at line {idx+1}")
        for j in range(idx, min(len(lines), idx+90)):
            print(f"{j+1}: {lines[j]}")
        break
