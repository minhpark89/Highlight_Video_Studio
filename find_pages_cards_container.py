from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where pages-cards-container is populated
pos = html.find('pages-cards-container')
while pos != -1:
    print(f"=== Match at {pos} ===")
    print(html[pos-50:pos+350])
    pos = html.find('pages-cards-container', pos+1)
