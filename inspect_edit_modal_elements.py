from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect modal-edit-group
pos = html.find('id="modal-edit-group"')
pos_end = html.find('<!-- MODAL XÁC NHẬN LÊN LỊCH', pos)
print("=== MODAL-EDIT-GROUP ===")
print(html[pos:pos_end])

# Check all getElementById in editGroupModal
pos_fn = html.find('async function editGroupModal')
print("\n=== editGroupModal JS ===")
print(html[pos_fn:pos_fn+1000])
