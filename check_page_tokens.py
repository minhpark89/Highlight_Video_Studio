import json
from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
if pages_file.exists():
    pages = json.loads(pages_file.read_text(encoding="utf-8"))
    tokens_assigned = [p.get("token_name") for p in pages]
    from collections import Counter
    print("Token distribution in pages.json:", Counter(tokens_assigned))
