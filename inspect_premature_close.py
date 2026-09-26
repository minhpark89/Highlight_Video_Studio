from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38657 where content-area closed early
pos = 38657
print("Snippet around 38657:")
print(html[pos-300:pos+300])
