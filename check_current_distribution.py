import json
from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
tokens_file = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")

pages = json.loads(pages_file.read_text(encoding="utf-8"))
tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

# Check pages tokens
from collections import Counter
p_toks = Counter(p.get("token_name") for p in pages)
print("Pages token distribution (unique tokens used):", len(p_toks))
print("Sample page tokens:", list(p_toks.items())[:5])

if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    post_toks = Counter(p.get("token_name") for p in posts)
    print("Posts token distribution (unique tokens used):", len(post_toks))
    print("Sample post tokens:", list(post_toks.items())[:5])
