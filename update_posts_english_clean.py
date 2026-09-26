import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))

for p in posts:
    slug = p.get("id", "post")
    article_url = f"https://bestnews.cfx.bz/article/{slug}"
    p["first_comment"] = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n👉 Scroll down the article to stream the complete high-definition video!"
    p["content"] = "Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.\n#reels #trending #highlight #viral #sports"
    p["hashtags"] = "#reels #trending #highlight #viral #sports"

posts_path.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
print("Successfully updated posts.json to English!")
