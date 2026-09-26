from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'pages-cards-container' is referenced in JavaScript
idx = 0
while True:
    idx = html.find('pages-cards-container', idx)
    if idx == -1: break
    print(f"Occurrence at {idx}:")
    print(html[max(0, idx-60):min(len(html), idx+300)])
    print("-" * 50)
    idx += 21
