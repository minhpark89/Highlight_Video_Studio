from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area ends and where pane-groups is
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')

# Extract the block of pane-groups and pane-posts
pg_match = re.search(r'<section id="pane-groups"[^>]*>.*?</section>\s*<section id="pane-posts"[^>]*>.*?</section>', html, re.DOTALL)
if pg_match:
    block = pg_match.group(0)
    html_without = html[:pg_match.start()] + html[pg_match.end():]
    
    # In html_without, find where content-area actually closes.
    # Where does content-area close?
    # Let's find id="pane-research" or id="pane-studio" inside content-area.
    # Let's place pane-groups and pane-posts immediately after pane-studio inside content-area!
    pos_studio = html_without.find('id="pane-studio"')
    pos_studio_end = html_without.find('</section>', pos_studio) + 10
    
    new_html = html_without[:pos_studio_end] + "\n\n" + block + html_without[pos_studio_end:]
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("Placed pane-groups directly inside content-area right after pane-studio!")
else:
    print("Could not match pane-groups and pane-posts")
