from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's search for "loadPostsTable"
pos = 0
matches = []
while True:
    pos = content.find("loadPostsTable", pos)
    if pos == -1: break
    line_no = content[:pos].count('\n') + 1
    matches.append((pos, line_no))
    pos += 15

print("Occurrences of loadPostsTable:")
for p, l in matches:
    print(f"Line {l}, pos {p}:")
    print(content[max(0, p-30):min(len(content), p+200)])
    print("-" * 40)
