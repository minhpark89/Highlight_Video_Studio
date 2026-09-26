from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

def get_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "NOT FOUND"
    pos_end = html.find('</section>', pos)
    return html[pos:pos_end]

with open(r"D:\Highlight_Video_Studio\curr_pane_pages.txt", "w", encoding="utf-8") as f:
    f.write(get_pane("pane-pages"))

with open(r"D:\Highlight_Video_Studio\curr_pane_groups.txt", "w", encoding="utf-8") as f:
    f.write(get_pane("pane-groups"))

print("Exported to txt successfully!")
