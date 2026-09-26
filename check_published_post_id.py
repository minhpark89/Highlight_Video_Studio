import json

posts = json.load(open(r"D:\Highlight_Video_Studio\posts.json", "r", encoding="utf-8"))
for p in posts:
    if p.get("status") == "published":
        print("Published post:", p["id"])
        print("  Page:", p.get("page_name"))
        print("  post_fb_id:", p.get("post_fb_id"))
        print("  fb_url:", p.get("fb_url"))
