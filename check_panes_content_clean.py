from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "Not found"
    end = html.find('</section>', pos)
    return html[pos:end]

print("=== PANE-PAGES ===")
p_pages = find_pane("pane-pages")
print(p_pages[:1200])

print("\n=== PANE-GROUPS ===")
p_groups = find_pane("pane-groups")
print(p_groups[:1200])
