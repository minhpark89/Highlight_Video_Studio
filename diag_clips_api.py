from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect /api/clips
pos = text.find('def get_all_clips')
print(text[pos:pos+600])

# Let's inspect where OUTPUT_DIR is defined
pos_out = text.find('OUTPUT_DIR =')
print(text[pos_out:pos_out+200])
