import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-publish-reel or modal-distribute-loha or whatever is shown in image 2
pos = text.find("First Comment tự động (Kèm Link website kéo traffic)")
print("Position:", pos)
if pos != -1:
    p_start = text.rfind("<div", 0, pos - 500)
    p_box = text.rfind("app-modal-box", 0, pos)
    p_overlay = text.rfind("app-modal-overlay", 0, pos)
    print("p_start:", p_start, "p_box:", p_box, "p_overlay:", p_overlay)
    print("Overlay snippet:")
    print(text[p_overlay:p_overlay+400])
    print("=== Modal around button ===")
    p_btn = text.find("Xác nhận Lên Lịch", pos)
    print(text[p_btn-200:p_btn+300])
