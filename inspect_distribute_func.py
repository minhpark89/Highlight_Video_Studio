from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect api_distribute_batch completely
pos = text.find('def api_distribute_batch')
pos_end = text.find('@app.route', pos+10)
print(text[pos:pos_end])
