from pathlib import Path
import re

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where api_publish_reel is defined
pos = text.find('def api_publish_reel')
print(text[pos:pos+1500])
