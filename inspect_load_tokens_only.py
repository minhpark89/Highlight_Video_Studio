from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where tokens-table-body is rendered in index.html
pos = html.find('async function loadTokensOnly()')
pos_end = html.find('</script>', pos)
print("=== loadTokensOnly snippet ===")
print(html[pos:pos+2500])
