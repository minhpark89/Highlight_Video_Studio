from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where pages-cards-container is populated in JS
idx = 0
found = []
while True:
    idx = html.find('pages-cards-container', idx)
    if idx == -1: break
    found.append(idx)
    idx += 22

print("Occurrences of pages-cards-container:", found)
for pos in found:
    print(f"--- Pos {pos} ---")
    print(html[pos-100:pos+300])
