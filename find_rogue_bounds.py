import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)

# Find where this rogue block starts and ends
# Look back for what opened it
start_p = text.rfind("<div", 0, pos - 200)
# Look back further
for i in range(1, 10):
    candidate = text.rfind("<div", 0, start_p - 10)
    print(f"Step back {i}: at {candidate}, tag: {text[candidate:candidate+40]!r}")
    start_p = candidate
    if "card" in text[candidate:candidate+40] or "panel" in text[candidate:candidate+40] or "modal" in text[candidate:candidate+40]:
        break

print("=== SNIPPET OF START ===")
print(text[start_p:start_p+300])

# Find where it ends
end_btn = text.find("Xác nhận Lên Lịch", pos)
end_div = text.find("</div>\n    </div>\n  </div>", end_btn)
if end_div == -1:
    end_div = text.find("</div>\n  </div>", end_btn)
if end_div == -1:
    end_div = text.find("</div>", end_btn + 100)

print(f"end_div: {end_div}")
print("=== SNIPPET OF END ===")
print(text[end_btn:end_div+50])
