from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's find pane-groups and pane-pages
def get_pane_snippet(pane_id):
    pos = html.find(f'id="{pane_id}"')
    if pos == -1: return "NOT FOUND"
    return html[pos:pos+1200]

print("=== PANE-GROUPS ===")
print(get_pane_snippet("pane-groups"))

print("\n=== PANE-PAGES ===")
print(get_pane_snippet("pane-pages"))

print("\n=== PANE-POSTS ===")
print(get_pane_snippet("pane-posts"))
