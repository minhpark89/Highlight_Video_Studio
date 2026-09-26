from pathlib import Path
import re

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = text.find('def api_distribute_batch')
print(text[pos:pos+1500])
