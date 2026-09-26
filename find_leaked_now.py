import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's search for "Hỗ trợ Hashtags"
pos = text.find("Hỗ trợ Hashtags")
print("Position:", pos)
if pos != -1:
    # Print 2000 chars around pos
    start = max(0, pos - 1000)
    end = min(len(text), pos + 1500)
    with open(BASE_DIR / "debug_leaked_form_around.html", "w", encoding="utf-8") as out:
        out.write(text[start:end])
    print("Wrote debug_leaked_form_around.html")
    print(text[start:start+500])
    print("...")
    print(text[pos:pos+500])
