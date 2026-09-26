from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'pages-cards-container' is in index.html
pos = 0
matches = []
while True:
    pos = html.find('pages-cards-container', pos)
    if pos == -1: break
    line_no = html[:pos].count('\n') + 1
    matches.append((pos, line_no))
    pos += 22

print("Occurrences of pages-cards-container:", matches)
for p, l in matches:
    print(f"Line {l}:")
    print(html[max(0, p-60):min(len(html), p+350)])
    print("-" * 50)
