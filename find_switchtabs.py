from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect all definitions of switchTab in index.html
pos = 0
matches = []
while True:
    p = html.find("switchTab", pos)
    if p == -1:
        break
    # check line
    line_start = html.rfind('\n', 0, p)
    line_end = html.find('\n', p)
    line = html[line_start+1:line_end].strip()
    if 'function' in line or '=' in line:
        matches.append((p, line))
    pos = p + 9

print("Matching switchTab assignments/definitions:")
for p, l in matches:
    print(f"Pos {p}: {l}")
