import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's find where "Xác nhận Lên Lịch (Schedule)" is
pos = text.find("Xác nhận Lên Lịch (Schedule)")
print("Position of 'Xác nhận Lên Lịch (Schedule)':", pos)
if pos != -1:
    # Print the modal container
    p_start = text.rfind("<div", 0, pos - 1500)
    p_modal = text.rfind("id=\"modal-", 0, pos)
    p_class = text.rfind("class=\"app-modal-overlay\"", 0, pos)
    print("p_modal:", p_modal, "p_class:", p_class)
    print("Modal header snippet:")
    print(text[p_class:p_class+400])
    print("--- Modal tail snippet ---")
    print(text[pos-400:pos+300])
