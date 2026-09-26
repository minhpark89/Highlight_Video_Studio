import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_box2 = text.find("<!-- Box 2: Tự nhiên hóa & Giới hạn an toàn -->")
print("Position of Box 2:", pos_box2)

pos_btn = text.find("Xác nhận Lên Lịch (Schedule)", pos_box2)
print("Position of btn:", pos_btn)

# Tìm đoạn kết thúc của khối rác này
# Nhìn ảnh của boss: khối này có các trường: Hỗ trợ Hashtags, First Comment, Hẹn giờ lên lịch, Giãn cách, Hủy bỏ, Xác nhận Lên Lịch
# Tìm thẻ đóng </div> cuối cùng của form này
pos_end = text.find("</form>", pos_btn)
if pos_end == -1:
    pos_end = text.find("</div>\n    </div>\n  </div>", pos_btn)
if pos_end == -1:
    pos_end = text.find("</div>", pos_btn + 150)

print(f"Rogue block goes from {pos_box2} to {pos_end}")
print("=== SNIPPET TO REMOVE ===")
print(text[pos_box2:pos_box2+400])
print("... middle ...")
print(text[pos_btn-100:pos_btn+300])
