from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where cachedPagesList is loaded in index.html
pos = html.find('cachedPagesList')
while pos != -1:
    print(f"=== Match at {pos} ===")
    print(html[max(0, pos-50):min(len(html), pos+350)])
    pos = html.find('cachedPagesList', pos+1)
