import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_start = text.find("<!-- Box 2: Tự nhiên hóa & Giới hạn an toàn -->")
pos_target = text.find("Bình luận đầu tiên tạo tò mò + link website", pos_start)

if pos_start != -1 and pos_target != -1:
    pos_end = text.find("</form>", pos_target)
    if pos_end == -1:
        pos_end = text.find("</div>\n    </div>\n  </div>", pos_target)
    if pos_end == -1:
        pos_end = text.find("Xác nhận Đăng Reel", pos_target)
        if pos_end != -1:
            pos_end = text.find("</div>\n      </div>", pos_end)
            if pos_end != -1:
                pos_end += len("</div>\n      </div>")
            else:
                pos_end = text.find("</div>", pos_end + 30) + 6

    print(f"Cutting rogue block from {pos_start} to {pos_end}")
    cut_content = text[pos_start:pos_end]
    print("Cut content length:", len(cut_content))
    
    text = text[:pos_start] + text[pos_end:]
    
    with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    if INDEX_ALT_PATH.exists():
        with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    print("Successfully deleted the leaked form from index.html!")
else:
    print("Could not find pos_start or pos_target!")
