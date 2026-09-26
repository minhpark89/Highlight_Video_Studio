from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "Not found"
    end = html.find('</section>', pos)
    return html[pos:end]

with open(r"D:\Highlight_Video_Studio\view_pages.html", "w", encoding="utf-8") as f:
    f.write(find_pane("pane-pages")[:3000])

with open(r"D:\Highlight_Video_Studio\view_posts.html", "w", encoding="utf-8") as f:
    f.write(find_pane("pane-posts")[:3000])

print("Wrote view files!")
