from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch writes to posted_clips.json
pos = text.find("def api_distribute_batch")
pos_end = text.find("save_posts(posts)", pos)
snippet = text[pos:pos_end+300]
print("Snippet around save_posts in api_distribute_batch:")
print(snippet[snippet.find("posted_set"):])
