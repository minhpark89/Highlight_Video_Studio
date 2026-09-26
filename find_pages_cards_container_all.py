from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'pages-cards-container' is in index.html
# Search for 'pages-cards-container' in script tags
pos = 0
matches = []
while True:
    pos = html.find('pages-cards-container', pos)
    if pos == -1: break
    matches.append(pos)
    pos += 22

print("Occurrences of pages-cards-container:", matches)
for p in matches:
    print("---", p, "---")
    print(html[p-100:p+300])
