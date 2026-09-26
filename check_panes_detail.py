from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "None"
    end = html.find('</section>', pos)
    return html[pos:end]

print("=== PANE-PAGES ===")
print(get_pane("pane-pages")[:1500])

print("\n=== PANE-GROUPS ===")
print(get_pane("pane-groups")[:1500])
