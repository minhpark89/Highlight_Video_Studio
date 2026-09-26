from pathlib import Path
import re

p = Path(r"D:\Highlight_Video_Studio\src\publisher\website_publisher.py")
text = p.read_text(encoding="utf-8")

# Let's inspect upload_long_video_to_public_stream
pos = text.find("def upload_long_video_to_public_stream")
pos2 = text.find("def extract_and_upload_article_assets", pos)
print("=== CURRENT upload_long_video_to_public_stream ===")
print(text[pos:pos2])
