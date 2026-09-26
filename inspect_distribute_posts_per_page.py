from pathlib import Path
import re

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect api_distribute_batch to support posts_per_page
pos = app_text.find('def api_distribute_batch')
pos_end = app_text.find('save_posts(posts)', pos)
print(app_text[pos:pos+1500])
