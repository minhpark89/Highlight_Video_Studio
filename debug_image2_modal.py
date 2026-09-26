import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position:", pos)
if pos != -1:
    p_box = text.rfind("app-modal-box", 0, pos)
    p_overlay = text.rfind("app-modal-overlay", 0, pos)
    print("p_box:", p_box, "p_overlay:", p_overlay)
    print("Modal container snippet:")
    print(text[p_overlay-50:p_overlay+250])
    
    # Check styles of this modal box
    p_end = text.find("</form>", pos)
    if p_end == -1: p_end = text.find("</div>\n  </div>", pos)
    print("Modal close snippet:")
    print(text[pos+200:pos+800])
