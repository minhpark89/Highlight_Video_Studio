from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_full_pane(name):
    start = html.find(f'id="{name}"')
    if start == -1: return "Not found"
    end = html.find('</section>', start)
    return html[start:end+10]

print("=== PANE-GROUPS ===")
print(get_full_pane("pane-groups")[:1500])

print("\n=== PANE-PAGES ===")
print(get_full_pane("pane-pages")[:1500])
