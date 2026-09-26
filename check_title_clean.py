import re
from pathlib import Path

path = Path(r"D:\Highlight_Video_Studio\src\publisher\website_publisher.py")
text = path.read_text(encoding="utf-8")

# Let's inspect where clean_title and slug are created
pos = text.find("def get_clip_metadata")
print(text[pos:pos+2000])
