import requests
import json

base_url = "http://127.0.0.1:5080"

# 1. Distribute batch of 100 clips for group_bm1 (1:1 allocation)
print("=== Step 1: Testing Batch Distribution (1:1 Allocation) ===")
res = requests.post(f"{base_url}/api/distribute/batch", json={
    "group_id": "group_bm1",
    "stagger_minutes": 15,
    "auto_first_comment": True,
    "delete_after_schedule": False
})
print("Status code:", res.status_code)
print("Response:", res.json())

# 2. Check posts in /api/posts
print("\n=== Step 2: Checking Posts Table ===")
posts = requests.get(f"{base_url}/api/posts").json()
print("Total scheduled posts:", len(posts))
if posts:
    p0 = posts[0]
    print(f"Sample Post 1:")
    print(f" - Title: {p0.get('title')}")
    print(f" - Media: {p0.get('media_file')}")
    print(f" - Target Page: {p0.get('page_name')} ({p0.get('page_id')})")
    print(f" - Token: {p0.get('token_name')}")
    print(f" - Scheduled Time: {p0.get('scheduled_time')}")
    print(f" - First Comment: {p0.get('first_comment')}")
