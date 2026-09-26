from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "Not found"
    end = html.find('</section>', pos)
    return html[pos:end]

print("=== PANE-PAGES ===")
print(find_pane("pane-pages")[:1500])

print("\n=== PANE-GROUPS ===")
print(find_pane("pane-groups")[:1500])
