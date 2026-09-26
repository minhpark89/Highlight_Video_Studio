from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where modal-add-group is
pos_m = html.find('id="modal-add-group"')
print("modal-add-group pos:", pos_m)
if pos_m != -1:
    pos_end = html.find('</div>\n  </div>\n</div>', pos_m)
    print(html[pos_m:pos_m+2000])

# Let's search openAddGroupModal
pos_fn = html.find('function openAddGroupModal')
print("\nopenAddGroupModal function:")
print(html[pos_fn:pos_fn+1000])
