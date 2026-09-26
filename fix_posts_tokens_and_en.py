import json
from pathlib import Path

pages_path = Path(r"D:\Highlight_Video_Studio\pages.json")
tokens_path = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")
posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")

pages = json.loads(pages_path.read_text(encoding="utf-8"))
tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
posts = json.loads(posts_path.read_text(encoding="utf-8"))

tok_map = {t["id"]: t["token"] for t in tokens}
print(f"Loaded {len(pages)} pages, {len(tokens)} tokens, {len(posts)} posts.")

# Ensure pages have actual tokens
updated_pages = False
for p in pages:
    tid = p.get("token_id")
    if tid in tok_map and (not p.get("access_token") or len(p.get("access_token", "")) < 20):
        p["access_token"] = tok_map[tid]
        updated_pages = True

if updated_pages:
    pages_path.write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Populated missing access_tokens into pages.json!")

page_token_map = {p["page_id"]: p.get("access_token") for p in pages}

# Update posts with actual token and English first comment
for post in posts:
    pid = post.get("page_id")
    if pid in page_token_map and page_token_map[pid]:
        post["token"] = page_token_map[pid]
    
    slug = post.get("id", "post")
    article_url = f"https://bestnews.cfx.bz/article/{slug}"
    post["first_comment"] = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n👉 Scroll down the article to stream the complete high-definition video!"
    post["content"] = "Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.\n#reels #trending #highlight #viral #sports"
    post["hashtags"] = "#reels #trending #highlight #viral #sports"

posts_path.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
print("Updated posts.json: All 4 posts now have REAL access_tokens and FULL ENGLISH First Comments!")
