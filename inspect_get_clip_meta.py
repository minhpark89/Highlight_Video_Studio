import re
from pathlib import Path

p = Path(r"D:\Highlight_Video_Studio\src\publisher\website_publisher.py")
text = p.read_text(encoding="utf-8")

# Let's inspect where clean_title is generated in get_clip_metadata
pos = text.find("def get_clip_metadata")
pos2 = text.find("def generate_llm_hook_image", pos)
print("=== CURRENT get_clip_metadata ===")
print(text[pos:pos2])
