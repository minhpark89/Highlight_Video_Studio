from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Đang nạp danh sách Fanpage Facebook" is in index.html
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# What function renders into this table/grid?
# Check loadTokensAndPages / renderFbPageCards
pos_fn = html.find('function renderFbPageCards()')
if pos_fn == -1: pos_fn = html.find('async function loadTokensAndPages()')
print("\n=== JS Function ===")
print(html[pos_fn:pos_fn+1200])
