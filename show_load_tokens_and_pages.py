from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 180100 to 180300 where loadTokensAndPages is defined
pos = html.find("async function loadTokensAndPages()")
print("=== loadTokensAndPages ===")
print(html[pos:pos+2500])
