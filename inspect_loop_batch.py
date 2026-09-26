from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's see the start of api_distribute_batch
pos = text.find("def api_distribute_batch():")
pos_loop = text.find("for idx, pid in enumerate(page_ids):", pos)
print("=== DISTRIBUTE BATCH LOOP START ===")
print(text[pos_loop:pos_loop+1500])
