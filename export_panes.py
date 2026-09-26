from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "Not found"
    end = html.find('</section>', pos)
    return html[pos:end]

with open("D:/Highlight_Video_Studio/debug_pages.txt", "w", encoding="utf-8") as f:
    f.write(find_pane("pane-pages"))

with open("D:/Highlight_Video_Studio/debug_groups.txt", "w", encoding="utf-8") as f:
    f.write(find_pane("pane-groups"))

with open("D:/Highlight_Video_Studio/debug_posts.txt", "w", encoding="utf-8") as f:
    f.write(find_pane("pane-posts"))

print("Exported debug panes successfully!")
