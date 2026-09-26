from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect loadTokensOnly in index.html
pos = html.find('async function loadTokensOnly')
print("loadTokensOnly at:", pos)
if pos != -1:
    pos_end = html.find('async function deleteTokenItem', pos)
    if pos_end == -1: pos_end = html.find('function deleteToken', pos)
    print(html[pos:pos+800])
