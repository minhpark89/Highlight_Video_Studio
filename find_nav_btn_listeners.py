from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where nav-btn click listeners are registered in the body script
matches = [m.start() for m in re.finditer(r'nav-btn', html)]
print("Total occurrences of nav-btn:", len(matches))
for p in matches[:10]:
    start = html.rfind('\n', 0, p)
    end = html.find('\n', p)
    print(html[start:end].strip())
