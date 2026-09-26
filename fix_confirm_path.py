import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Fix the confirm alert backslash issue:
# In runLoHaBatchSchedule, it had:
# if (!confirm(`Xác nhận quét kho video (D:\\Highlight_Video_Studio\\output) ...`))
# In template literals, `D:\Highlight_Video_Studio\output` strips backslashes if not quadruple escaped!
# Let's replace it with clean display:
html = html.replace('D:\\\\Highlight_Video_Studio\\\\output', 'D:/Highlight_Video_Studio/output')
html = html.replace('D:\\Highlight_Video_Studio\\output', 'D:/Highlight_Video_Studio/output')

INDEX_PATH.write_text(html, encoding="utf-8")
print("Fixed path display in confirm dialog!")
