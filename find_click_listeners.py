from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

matches = [m.start() for m in re.finditer(r'addEventListener\(.+click', html)]
print("Click listeners in index.html:", len(matches))
for pos in matches:
    print(html[pos-50:pos+250])
    print("="*40)
