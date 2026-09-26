from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect modal-add-group to create a matching modal-edit-group
pos_add_modal = html.find('id="modal-add-group"')
pos_add_end = html.find('</div>\n    </div>\n  </div>', pos_add_modal)
add_modal_html = html[pos_add_modal-30:pos_add_end+25]
print("add_modal length:", len(add_modal_html))
print(add_modal_html[:500])
