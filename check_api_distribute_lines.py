from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is
pos = app_py.find("def api_distribute_batch():")
pos_end = app_py.find("@app.route", pos+10)
print("=== api_distribute_batch ===")
print(app_py[pos:pos_end])
