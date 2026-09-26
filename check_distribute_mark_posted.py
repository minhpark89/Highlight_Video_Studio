from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where /api/distribute/batch writes to posted_clips.json
# Look around line 1432:
pos = app_py.find("api_distribute_batch")
pos_end = app_py.find("@app.route", pos+10)
snippet = app_py[pos:pos_end]

for line in snippet.splitlines():
    if "posted_clips" in line:
        print(line)
