import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Check how groups are displayed and handled
pos_groups = text.find('stat-total-groups')
print("stat-total-groups pos:", pos_groups)
if pos_groups != -1:
    print(text[pos_groups-100:pos_groups+400])

pos_modal_grp = text.find('id="modal-add-group"')
print("modal-add-group pos:", pos_modal_grp)
if pos_modal_grp != -1:
    print(text[pos_modal_grp:pos_modal_grp+1200])
