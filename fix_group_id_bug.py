from pathlib import Path
import json

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_save_group:
pos = text.find('def api_save_group')
pos_end = text.find('@app.route', pos+10)
print("=== api_save_group ===")
print(text[pos:pos_end])
