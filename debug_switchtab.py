from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect switchTab implementation in <head> and in <body>
import re
matches = [m.start() for m in re.finditer(r'function switchTab|window\.switchTab', html)]
print("switchTab matches at:", matches)
for pos in matches:
    print(html[pos:pos+700])
    print("="*50)
