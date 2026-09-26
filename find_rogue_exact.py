import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Tìm vị trí chính xác của đoạn "Cơ chế phát video từ kho"
pos = text.find("Cơ chế phát video từ kho")
print("Position:", pos)
if pos != -1:
    # Tìm thẻ <div cha chứa đoạn này
    # Tìm ngược lên để tìm container
    start_tag = text.rfind('<div class="card"', 0, pos)
    if start_tag == -1:
        start_tag = text.rfind('<div', 0, pos - 200)
    
    # Tìm thẻ đóng tương ứng
    end_tag = text.find('</div>\n        </div>', pos)
    if end_tag == -1:
        end_tag = text.find('</div>', pos + 300)
    
    print("start_tag pos:", start_tag)
    print("end_tag pos:", end_tag)
    print("Snippet to remove:")
    print(text[start_tag:end_tag+15])
