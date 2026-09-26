from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "None"
    end = html.find('</section>', pos)
    return html[pos:end]

print("=== PANE-POSTS BUTTONS ===")
posts_pane = get_pane("pane-posts")
print(posts_pane[:1200])
