import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Tìm vị trí của modal-publish-reel (Ảnh 2 của boss chính là modal này đang bị lỗi CSS/vỡ layout che mất)
pos_pub = text.find('id="modal-publish-reel"')
print("modal-publish-reel pos:", pos_pub)
if pos_pub != -1:
    print(text[pos_pub:pos_pub+2000])

# 2. Kiểm tra modal-add-group (Ảnh 1 của boss: danh sách chọn page chỉ có ô checkbox trắng và tên bên phải, thiếu avatar và thông số)
pos_grp = text.find('id="modal-add-group"')
print("modal-add-group pos:", pos_grp)
