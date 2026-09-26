from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')

# In diag_exact_gap.py:
# Layout Info: {'paneParentId': 'main', 'paneParentTag': 'MAIN', ...}
# caRect height: 674.265625
# Notice: <div id="content-area"> is closed, and then <section id="pane-groups"> is placed after it.
# So #content-area sits above #pane-groups, taking 674px of empty flex space!

# Let's cut out pane-groups and pane-posts
pg_match = re.search(r'<!-- =+ -->\s*<!-- TAB 1: NHÓM TRANG.*?<!-- TAB 4: QUẢN LÝ BÀI ĐĂNG.*?</section>', html, re.DOTALL)
if not pg_match:
    pg_match = re.search(r'<section id="pane-groups"[^>]*>.*?</section>\s*<section id="pane-posts"[^>]*>.*?</section>', html, re.DOTALL)

print("pg_match found:", pg_match is not None)
if pg_match:
    block = pg_match.group(0)
    # Remove block from current position
    html_without = html[:pg_match.start()] + html[pg_match.end():]
    
    # Place it directly inside content-area right after <div id="content-area">\n
    pos_ca_in_clean = html_without.find('id="content-area"')
    pos_ca_tag_end = html_without.find('>', pos_ca_in_clean) + 1
    
    new_html = html_without[:pos_ca_tag_end] + "\n\n" + block + "\n" + html_without[pos_ca_tag_end:]
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("Successfully placed pane-groups and pane-posts at TOP of #content-area!")
