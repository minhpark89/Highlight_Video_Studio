from pathlib import Path
import re

p = Path(r"D:\Highlight_Video_Studio\src\publisher\website_publisher.py")
text = p.read_text(encoding="utf-8")

# Let's inspect get_clip_metadata
pos = text.find("def get_clip_metadata")
print(text[pos:pos+1500])
