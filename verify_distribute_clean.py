import json
from pathlib import Path

# 1. Reset posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Check web/app.py to ensure api_distribute_batch NEVER writes to posted_clips.json
app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find("def api_distribute_batch")
pos_end = app_py.find("@app.route", pos+20)
dist_code = app_py[pos:pos_end]

if "posted_file.write_text" in dist_code or "posted_clips.json" in dist_code:
    print("Found posted_clips reference in api_distribute_batch:")
    for line in dist_code.splitlines():
        if "posted_file" in line or "posted_clips" in line:
            print("  ", line)
else:
    print("api_distribute_batch does not write to posted_clips.json!")
