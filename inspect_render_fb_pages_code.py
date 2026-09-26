from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect renderFbPageCards definition
pos = html.find("function renderFbPageCards")
if pos == -1: pos = html.find("async function renderFbPageCards")
print("renderFbPageCards pos:", pos)
if pos != -1:
    print(html[pos:pos+2000])
