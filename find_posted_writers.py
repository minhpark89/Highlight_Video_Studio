from pathlib import Path

# Search where posted_clips.json was written to get 8 items
for p in Path(r"D:\Highlight_Video_Studio").glob("*.py"):
    txt = p.read_text(encoding="utf-8")
    if "posted_clips.json" in txt and ("write" in txt or "dump" in txt or "append" in txt):
        print("File writes to posted_clips.json:", p.name)
