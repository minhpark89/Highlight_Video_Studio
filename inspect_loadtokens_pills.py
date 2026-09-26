from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect loadTokensOnly function in index.html
pos = html.find('async function loadTokensOnly(')
if pos == -1: pos = html.find('async function loadTokensOnly()')
print("loadTokensOnly at:", pos)
if pos != -1:
    pos_end = html.find('async function deleteSingleToken', pos)
    if pos_end == -1: pos_end = html.find('async function deleteTokenItem', pos)
    print(html[pos:pos+1500])
