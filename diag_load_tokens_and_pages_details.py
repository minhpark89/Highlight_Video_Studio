from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages around line 180119
pos = html.find("async function loadTokensAndPages()")
pos_end = html.find("function renderFilteredPages", pos)
print("=== loadTokensAndPages ===")
print(html[pos:pos+2500])

# Check what renderFilteredPages does and what container it writes to
pos_rfp = html.find("function renderFilteredPages()")
print("\n=== renderFilteredPages ===")
print(html[pos_render_rfp := pos_rfp:pos_render_rfp+2500])
