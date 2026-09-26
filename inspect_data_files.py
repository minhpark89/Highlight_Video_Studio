import json

# Check posts.json
try:
    with open('D:/Highlight_Video_Studio/posts.json', 'r', encoding='utf-8') as f:
        posts = json.load(f)
    print(f"posts.json has {len(posts)} items")
    if posts:
        print("Sample post:", json.dumps(posts[0], indent=2, ensure_ascii=False))
except Exception as e:
    print("posts.json error:", e)

# Check posted_clips.json
try:
    with open('D:/Highlight_Video_Studio/posted_clips.json', 'r', encoding='utf-8') as f:
        posted = json.load(f)
    print(f"posted_clips.json has {len(posted)} items")
except Exception as e:
    print("posted_clips.json error:", e)

# Check page_groups.json
try:
    with open('D:/Highlight_Video_Studio/page_groups.json', 'r', encoding='utf-8') as f:
        groups = json.load(f)
    print(f"page_groups.json has {len(groups)} items")
    for g in groups:
        print(f" - Group {g.get('name')} (id: {g.get('id')}): {len(g.get('page_ids', []))} pages")
except Exception as e:
    print("page_groups.json error:", e)
