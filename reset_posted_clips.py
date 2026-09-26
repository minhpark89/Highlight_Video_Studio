import json
from pathlib import Path

posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
# Reset posted_clips.json to empty list or only truly published clips
posted_file.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to [] successfully!")
