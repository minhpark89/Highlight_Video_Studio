import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)
# Xem ngược lên để tìm thẻ mở bao bọc khối này
start_idx = text.rfind("<div", 0, pos - 200)
# Look back further to see what section or div it is in
print("Snippet around start:")
print(text[pos-600:pos+200])

print("Snippet around button Xác nhận Lên Lịch:")
pos_btn = text.find("Xác nhận Lên Lịch", pos)
print(text[pos_btn-100:pos_btn+300])
