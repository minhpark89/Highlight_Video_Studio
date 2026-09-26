from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1:
        return f"Not found {name}"
    pos_end = html.find('</section>', pos)
    return html[pos:pos+1500]

print("=== PANE-GROUPS ===")
print(find_pane("pane-groups"))

print("\n=== PANE-PAGES ===")
print(find_pane("pane-pages"))
