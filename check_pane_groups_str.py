from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "Not found"
    end = html.find('</section>', pos)
    return html[pos:end]

txt = find_pane("pane-groups")
print("=== PANE-GROUPS LENGTH:", len(txt))
print(txt[:2500])
