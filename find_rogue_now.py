import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Bình luận đầu tiên tạo tò mò + link website")
print("Position:", pos)
if pos != -1:
    p_start = text.rfind("<div", 0, pos - 500)
    p_end = text.find("Xác nhận Lên Lịch", pos)
    p_end_div = text.find("</div>\n    </div>\n  </div>", p_end)
    print("p_start:", p_start, "p_end:", p_end, "p_end_div:", p_end_div)
    with open(BASE_DIR / "rogue_leak.html", "w", encoding="utf-8") as f_out:
        f_out.write(text[p_start:p_end+200])
    print("Wrote rogue_leak.html")
    print(text[pos-200:pos+300])
