from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where pages-cards-container is referenced in JavaScript
idx = 0
matches = []
while True:
    idx = html.find('pages-cards-container', idx)
    if idx == -1: break
    matches.append(idx)
    idx += 22

print("Occurrences of pages-cards-container:", len(matches))
for p in matches:
    print(f"--- Pos {p} ---")
    print(html[max(0, p-60):min(len(html), p+400)])
