from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find('posts-table-body')
print("posts-table-body pos:", pos)

# Find all occurrences of loadPostsTable in html
matches = []
pos_fn = 0
while True:
    pos_fn = html.find("loadPostsTable", pos_fn)
    if pos_fn == -1: break
    matches.append(pos_fn)
    pos_fn += 15

print("loadPostsTable occurrences:", len(matches))
for m in matches:
    if "function" in html[m-20:m+20]:
        print(f"Def at {m}:")
        print(html[m-20:m+600])
        print("="*40)
