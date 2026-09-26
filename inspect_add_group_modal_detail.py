from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where modal-add-group is to design modal-edit-group
pos = html.find('id="modal-add-group"')
pos_end = html.find('</div>\n    </div>\n  </div>', pos)
print("=== modal-add-group ===")
print(html[pos:pos+1500])
