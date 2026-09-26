from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "None"
    end = html.find('</section>', pos)
    return html[pos:end]

with open(r"D:\Highlight_Video_Studio\pane_pages.html", "w", encoding="utf-8") as f:
    f.write(get_pane("pane-pages"))

with open(r"D:\Highlight_Video_Studio\pane_groups.html", "w", encoding="utf-8") as f:
    f.write(get_pane("pane-groups"))

with open(r"D:\Highlight_Video_Studio\pane_posts.html", "w", encoding="utf-8") as f:
    f.write(get_pane("pane-posts"))

print("Wrote pane files successfully!")
