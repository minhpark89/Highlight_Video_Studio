import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_start = text.find("<!-- Box 2: Tự nhiên hóa & Giới hạn an toàn -->")
print("Box 2 pos:", pos_start)

# Tìm xem đoạn này kết thúc ở đâu: tìm thẻ </form> hoặc nút Xác nhận Lên Lịch
pos_target = text.find("Bình luận đầu tiên tạo tò mò + link website", pos_start)
print("pos_target:", pos_target)

# Tìm tiếp thẻ </form> hoặc thẻ đóng div kết thúc khối giao diện này
pos_end = text.find("</form>", pos_target)
if pos_end == -1:
    pos_end = text.find("</div>\n    </div>\n  </div>", pos_target)
if pos_end != -1:
    # Lấy luôn thẻ đóng
    pos_end_tag = text.find(">", pos_end) + 1
    print(f"Rogue block range: {pos_start} to {pos_end_tag}")
    snippet = text[pos_start:pos_end_tag]
    print("=== SNIPPET LENGTH ===", len(snippet))
    print(snippet[:300])
    print("...")
    print(snippet[-300:])
    with open(BASE_DIR / "exact_rogue_to_cut.html", "w", encoding="utf-8") as f_out:
        f_out.write(snippet)
else:
    print("Could not find end tag!")
