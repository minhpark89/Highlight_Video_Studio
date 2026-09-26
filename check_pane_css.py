from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for main, .pane, #pane-groups
css_matches = re.findall(r'(\.pane[^{]*\{[^}]+\})', html)
print("CSS for .pane:")
for m in css_matches:
    print(m)

main_matches = re.findall(r'(#main[^{]*\{[^}]+\})', html)
print("CSS for #main:")
for m in main_matches:
    print(m)
