import json
from pathlib import Path

# Check token_groups.json
tg_file = Path(r"D:\Highlight_Video_Studio\token_groups.json")
if tg_file.exists():
    print("token_groups.json:", tg_file.read_text(encoding="utf-8"))
else:
    print("token_groups.json does not exist!")
