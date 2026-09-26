import json
from pathlib import Path

pages = json.loads(Path(r"D:\Highlight_Video_Studio\pages.json").read_text(encoding="utf-8"))
posts = json.loads(Path(r"D:\Highlight_Video_Studio\posts.json").read_text(encoding="utf-8"))
tokens = json.loads(Path(r"D:\Highlight_Video_Studio\tokens_vault.json").read_text(encoding="utf-8"))

print("Tokens in vault:", len(tokens))
for t in tokens[:3]:
    print("Token sample:", t.get("name"), "token len:", len(t.get("token", "")))

p_map = {p["page_id"]: p for p in pages}
for post in posts:
    pid = post.get("page_id")
    page_data = p_map.get(pid, {})
    print(f"Post {post['id']} -> Page {pid}:")
    print(f"  post token len: {len(post.get('token', ''))}")
    print(f"  page access_token len: {len(page_data.get('access_token', ''))}")
    print(f"  page token_id: {page_data.get('token_id')}")
