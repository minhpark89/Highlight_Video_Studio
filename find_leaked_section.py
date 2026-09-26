import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where "Cơ chế phát video từ kho" is in index.html
pos = text.find("Cơ chế phát video từ kho")
print("Position:", pos)
if pos != -1:
    # Print the section from <section id=... up to </section>
    p_sec = text.rfind("<section", 0, pos)
    p_end = text.find("</section>", pos)
    print("Section start:", p_sec, "end:", p_end)
    print("=== SECTION HEADER ===")
    print(text[p_sec:p_sec+300])
    print("=== LEAKED PART ===")
    print(text[pos-100:pos+500])
