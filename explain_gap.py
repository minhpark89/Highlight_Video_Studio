from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')

# We saw in diag_exact_gap.py:
# Layout Info: {'paneParentId': 'main', 'paneParentTag': 'MAIN', 'caChildren': ...}
# When pane-groups was active, pane-groups was a sibling of content-area, sitting below it!
# And inside content-area, .pane has display:none, but why did content-area have height 674px?
# Because #content-area has CSS:
# flex: 1; min-height: ... or height of content-area!
# In CSS:
# #content-area {
#   flex: 1;
#   padding: 24px 28px 60px;
#   max-width: 1540px;
#   width: 100%;
#   margin: 0 auto;
# }
# Since #main has display: flex; flex-direction: column; min-height: 100vh;
# #content-area has flex: 1!
# When pane-groups is OUTSIDE #content-area (placed after #content-area),
# #content-area expands to fill all available flex space (674px of empty height),
# and pushes pane-groups down to the bottom of the screen!

print("THAT IS THE EXACT REASON! pane-groups is outside #content-area!")
