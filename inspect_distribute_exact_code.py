from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is
pos = text.find("def api_distribute_batch():")
pos_end = text.find("def handle_schedule_rules():", pos)
print("api_distribute_batch length:", pos_end - pos)
print(text[pos:pos_end])
