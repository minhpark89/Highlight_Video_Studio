import requests

# 1. Test /api/schedule/rules
r_rules = requests.get("http://127.0.0.1:5080/api/schedule/rules")
print("1. /api/schedule/rules status:", r_rules.status_code, r_rules.json())

# 2. Test /api/pages
r_pages = requests.get("http://127.0.0.1:5080/api/pages")
print("2. /api/pages status:", r_pages.status_code, "Count:", len(r_pages.json().get("pages", [])))

# 3. Test /api/clips
r_clips = requests.get("http://127.0.0.1:5080/api/clips")
clips = r_clips.json()
print("3. /api/clips status:", r_clips.status_code, "Total:", len(clips), "is_posted:", len([c for c in clips if c.get("is_posted")]))

# 4. Test /api/posts
r_posts = requests.get("http://127.0.0.1:5080/api/posts")
print("4. /api/posts status:", r_posts.status_code, "Count:", len(r_posts.json()))
