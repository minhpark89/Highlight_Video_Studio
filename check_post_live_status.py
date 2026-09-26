import json

posts = json.load(open(r"D:\Highlight_Video_Studio\posts.json", "r", encoding="utf-8"))
for p in posts:
    print(f"ID: {p['id']}, Page: {p['page_name']}, Status: {p['status']}, Sched: {p['scheduled_time']}, PostFBId: {p.get('post_fb_id')}")
