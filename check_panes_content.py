from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_snippet(target, length=2000):
    idx = html.find(target)
    if idx == -1: return "NOT FOUND"
    return html[idx:idx+length]

print("=== PANE-PAGES ===")
print(get_snippet('id="pane-pages"'))

print("\n=== PANE-GROUPS ===")
print(get_snippet('id="pane-groups"'))
