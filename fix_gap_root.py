from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area is and how all panes are structured
pos_ca = html.find('id="content-area"')
pos_main = html.find('<main id="main">')
pos_main_end = html.find('</main>')

print(f"main: {pos_main}, content-area: {pos_ca}, main_end: {pos_main_end}")

# In diag_exact_gap.py, we saw:
# Layout Info: {'paneParentId': 'main', 'paneParentTag': 'MAIN', ...}
# caRect height: 674.265625
# That meant pane-groups was NOT a child of content-area, but a direct child of <main>!
# Why? Because <div id="content-area"> was closed BEFORE pane-groups!

# Let's find where the closing </div> of content-area is.
# In trace_ca_exact.py:
# content-area CLOSES at index 38657!
# Let's see what is at 38657:
print("=== Around index 38657 ===")
print(html[38600:38750])
