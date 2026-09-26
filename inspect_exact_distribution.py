import json
from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
tokens_file = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")

pages = json.loads(pages_file.read_text(encoding="utf-8"))
tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

from collections import Counter
print("Tokens available:", len(tokens))
print("Pages count:", len(pages))
print("Pages token distribution:", Counter(p.get("token_name") for p in pages))

if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    print("Posts count:", len(posts))
    print("Posts token distribution:", Counter(p.get("token_name") for p in posts))
