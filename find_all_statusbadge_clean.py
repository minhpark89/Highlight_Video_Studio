from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect where statusBadge is defined in templates/index.html
pos = 0
matches = []
while True:
    pos = html.find("statusBadge", pos)
    if pos == -1: break
    matches.append(pos)
    pos += 11

print("Found statusBadge occurrences:", len(matches))
for p in matches:
    print(f"--- Pos {p} ---")
    print(html[p-30:p+300])
