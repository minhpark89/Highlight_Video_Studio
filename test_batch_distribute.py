import requests
import json

base_url = "http://127.0.0.1:5080"

# 1. Fetch groups
res_g = requests.get(f"{base_url}/api/groups")
print("Groups:", res_g.status_code, res_g.json())

# 2. Fetch clips
res_c = requests.get(f"{base_url}/api/clips")
clips_data = res_c.json()
print("Total clips:", len(clips_data.get("clips", [])))

# 3. Fetch posts
res_p = requests.get(f"{base_url}/api/posts")
print("Posts before:", len(res_p.json()))

# 4. Try distributing batch for group_bm1 with delete_after_schedule=False
res_dist = requests.post(f"{base_url}/api/distribute/batch", json={
    "group_id": "group_bm1",
    "stagger_minutes": 15,
    "auto_first_comment": True,
    "delete_after_schedule": False
})
print("Distribute response:", res_dist.status_code, res_dist.json())

# 5. Check posts after
res_p2 = requests.get(f"{base_url}/api/posts")
print("Posts after distribute:", len(res_p2.json()))
if res_p2.json():
    print("Sample scheduled post:", json.dumps(res_p2.json()[0], indent=2, ensure_ascii=False))
