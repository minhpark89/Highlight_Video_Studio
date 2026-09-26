import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)

# Xem ngược lên từ pos để tìm xem nó bắt đầu từ đâu
start_p = text.rfind("<!-- Box 2", 0, pos)
if start_p == -1:
    start_p = text.rfind("<div", 0, pos - 300)

# Xem xuôi xuống để tìm nút Xác nhận Lên Lịch (Schedule) và thẻ đóng của nó
end_p = text.find("Xác nhận Lên Lịch (Schedule)", pos)
print("start_p:", start_p, "end_p:", end_p)

# In đoạn từ end_p đến 500 ký tự tiếp theo để xem kết thúc ở đâu
if end_p != -1:
    print("Snippet after end_p:")
    print(text[end_p:end_p+400])
    
    # Tìm thẻ đóng của form/div này
    close_div = text.find("</div>\n    </div>\n  </div>", end_p)
    if close_div == -1:
        close_div = text.find("</div>\n  </div>", end_p)
    if close_div == -1:
        close_div = text.find("</div>", end_p + 100)
    print("close_div:", close_div)
