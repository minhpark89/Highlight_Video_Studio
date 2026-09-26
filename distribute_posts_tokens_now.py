import json
from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
tokens_file = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")

pages = json.loads(pages_file.read_text(encoding="utf-8"))
tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

# Distribute 31 tokens evenly across 100 pages
# Page 0 -> Token 0, Page 1 -> Token 1, ... Page 30 -> Token 30, Page 31 -> Token 0 ...
for i, p in enumerate(pages):
    tok = tokens[i % len(tokens)]
    p["token_id"] = tok.get("id")
    p["token_name"] = tok.get("name")

pages_file.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")

if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    page_map = {p["page_id"]: p["token_name"] for p in pages}
    for post in posts:
        pid = post.get("page_id")
        if pid in page_map:
            post["token_name"] = page_map[pid]
    posts_file.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

print("Done! Check posts token distribution:")
from collections import Counter
posts = json.loads(posts_file.read_text(encoding="utf-8"))
c = Counter(p.get("token_name") for p in posts)
print("Unique tokens in posts:", len(c))
print("Sample tokens:", list(c.items())[:6])
