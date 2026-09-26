from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')

print(f"Content-area opens at {pos_ca}")
print(f"pane-groups at {pos_pg}")
print(f"pane-posts at {pos_pp}")

# Let's find all closing </div> tags between pos_ca and pos_pg
# We want pane-groups and pane-posts to be INSIDE #content-area, not after it!
# Let's inspect where the closing </div> of content-area is
pos_main = html.find('<main id="main">')
pos_main_end = html.find('</main>')

# Let's extract pane-groups and pane-posts block
pg_match = re.search(r'<section id="pane-groups"[^>]*>.*?</section>\s*<section id="pane-posts"[^>]*>.*?</section>', html, re.DOTALL)
if not pg_match:
    pg_match = re.search(r'<!-- =+ -->\s*<!-- TAB 1: NHÓM TRANG.*?<!-- TAB 4: QUẢN LÝ BÀI ĐĂNG.*?</section>', html, re.DOTALL)

print("Matched block:", pg_match is not None)
if pg_match:
    block = pg_match.group(0)
    # Remove it first
    html_clean = html[:pg_match.start()] + html[pg_match.end():]
    
    # Now place it inside content-area right after pane-studio or pane-research or pane-jobs
    # Let's place it right before the last closing </div> of content-area
    # Find pane-website end inside content-area
    pos_pw = html_clean.find('id="pane-website"')
    pos_pw_end = html_clean.find('</section>', pos_pw) + 10
    
    # Insert block right after pane-website, making sure it is inside content-area
    new_html = html_clean[:pos_pw_end] + "\n\n" + block + html_clean[pos_pw_end:]
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("Placed block right after pane-website!")
