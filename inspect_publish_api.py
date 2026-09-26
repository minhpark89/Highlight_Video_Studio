from pathlib import Path
import re

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

pos = app_text.find('def api_publish_reel')
pos_end = app_text.find('@app.route', pos+10)
print("=== api_publish_reel ===")
print(app_text[pos:pos_end])
