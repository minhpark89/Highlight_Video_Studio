import requests
import json

base_url = "http://127.0.0.1:5080"
posts = requests.get(f"{base_url}/api/posts").json()
print("Total scheduled posts:", len(posts))
for i, p in enumerate(posts[:5]):
    print(f"[{i+1}] Page: {p['page_name']} | Clip: {p['media_file']} | Time: {p['scheduled_time']}")
    print(f"    First comment: {p['first_comment'][:80]}...")
