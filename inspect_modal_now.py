from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect modal-edit-group in index.html
pos = html.find('id="modal-edit-group"')
pos_end = html.find('<!-- MODAL XÁC NHẬN LÊN LỊCH', pos)
print("=== MODAL-EDIT-GROUP CURRENT HTML ===")
print(html[pos:pos_end])
