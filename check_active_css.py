from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for #content-area and .pane
pos_css = html.find('#content-area {')
print(html[pos_css:pos_css+400])

# Look at how .pane.active works
pos_pane_css = html.find('.pane {')
print(html[pos_pane_css:pos_pane_css+300])
