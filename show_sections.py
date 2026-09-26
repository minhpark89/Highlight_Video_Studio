from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def show_section(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return f"Not found {name}"
    pos_end = html.find('</section>', pos)
    return html[pos:pos_end]

print("=== PANE-GROUPS ===")
print(show_section("pane-groups")[:2000])

print("\n=== PANE-PAGES ===")
print(show_section("pane-pages")[:2000])
