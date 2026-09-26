import json
from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
tokens_file = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")

pages = json.loads(pages_file.read_text(encoding="utf-8"))
tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

# Check unique tokens in posts.json
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    from collections import Counter
    c = Counter(p.get("token_name") for p in posts)
    print("Posts total:", len(posts))
    print("Unique tokens in posts:", len(c))
    print("Tokens sample:", list(c.items())[:6])
