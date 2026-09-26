from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area opens and closes, and where pane-groups is located
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')

print(f"Content-area opens at {pos_ca}, pane-groups at {pos_pg}")

# Find where content-area was closed
# Let's search for </div> right before pane-groups
pos_before_pg = html.rfind('</div>', 0, pos_pg)
print(f"Last </div> before pane-groups at {pos_before_pg}")
print("Snippet around last </div> before pane-groups:")
print(html[pos_before_pg-100:pos_before_pg+200])
