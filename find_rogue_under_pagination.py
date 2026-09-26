import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_h = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos_h)

# Tìm xem đoạn này bắt đầu từ đâu sau id="pages-pagination"
pos_pag = text.find('id="pages-pagination"')
print("Position of 'pages-pagination':", pos_pag)

# Đoạn nằm giữa pages-pagination và thẻ đóng </section> của pane-pages
pos_sec = text.find("</section>", pos_pag)
print("Position of </section> after pagination:", pos_sec)

print("=== CONTENT BETWEEN PAGINATION AND END OF SECTION ===")
print(text[pos_pag:pos_sec+15])
