from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pages-tbody and renderFbPageCards
pos = html.find('id="pages-tbody"')
print("pages-tbody pos:", pos)

# Find all occurrences of pages-tbody in html
idx = 0
while True:
    idx = html.find('pages-tbody', idx)
    if idx == -1: break
    print(f"Occurrence at {idx}:")
    print(html[max(0, idx-50):min(len(html), idx+200)])
    print("-" * 40)
    idx += 11
