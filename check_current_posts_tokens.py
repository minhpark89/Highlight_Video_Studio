import json
from pathlib import Path

posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    from collections import Counter
    toks = Counter(p.get("token_name") for p in posts)
    print("Total posts:", len(posts))
    print("Unique tokens:", len(toks))
    print("Token sample:", list(toks.items())[:6])
