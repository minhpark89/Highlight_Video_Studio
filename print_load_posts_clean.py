from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 5060 to 5200 in templates/index.html to see loadPostsTable
lines = html.splitlines()
found_start = -1
for idx, l in enumerate(lines):
    if "async function loadPostsTable" in l or "function loadPostsTable" in l:
        found_start = idx
        break

print(f"loadPostsTable starts at line {found_start+1}")
for i in range(found_start, min(len(lines), found_start + 80)):
    print(f"{i+1}: {lines[i]}")
