from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect loadTokensOnly function in index.html
pos = html.find('async function loadTokensOnly()')
pos_end = html.find('</script>', pos)
print("loadTokensOnly code:")
print(html[pos:pos+1500])
