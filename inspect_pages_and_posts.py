from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def find_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1:
        return f"Not found {name}"
    pos_end = html.find('</section>', pos)
    return html[pos:pos_end+10]

print("=== PANE-PAGES FULL ===")
print(find_pane("pane-pages")[:2500])

print("\n=== PANE-POSTS BUTTONS ===")
pos_p = html.find('id="pane-posts"')
print(html[pos_p:pos_p+1500])
