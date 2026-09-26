from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #pane-groups and #pane-posts are placed.
# In diag_why_pushed_down.py:
# content-area height is 674px, and pane-groups top is 738px!
# That means pane-groups is AFTER #content-area!
# Let's extract the block of pane-groups and pane-posts and move them INSIDE #content-area right before </div> of #content-area!

pg_match = re.search(r'<!-- =+ -->\s*<!-- TAB 1: NHÓM TRANG.*?<!-- TAB 4: QUẢN LÝ BÀI ĐĂNG.*?</section>', html, re.DOTALL)
if not pg_match:
    pg_match = re.search(r'<section id="pane-groups"[^>]*>.*?</section>\s*<section id="pane-posts"[^>]*>.*?</section>', html, re.DOTALL)

print("pg_match found:", pg_match is not None)
if pg_match:
    block = pg_match.group(0)
    print("Block length:", len(block))
    # Cut it out
    html_without_block = html[:pg_match.start()] + html[pg_match.end():]
    
    # Now find where the last section inside #content-area is (e.g., pane-website)
    pos_pw = html_without_block.find('id="pane-website"')
    pos_pw_end = html_without_block.find('</section>', pos_pw) + 10
    
    # Insert block right after pane-website, still inside #content-area
    new_html = html_without_block[:pos_pw_end] + "\n\n" + block + html_without_block[pos_pw_end:]
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("Successfully moved pane-groups and pane-posts INSIDE #content-area!")
else:
    print("Could not match pane-groups and pane-posts block")
