import requests
import json

base_url = "http://127.0.0.1:5080"

# Fetch token-groups
try:
    r = requests.get(f"{base_url}/api/token-groups")
    print("token-groups:", r.status_code, r.json())
except Exception as e:
    print("Err token-groups:", e)

# Fetch posts
try:
    r = requests.get(f"{base_url}/api/posts")
    posts = r.json()
    print("Total posts:", len(posts))
    from collections import Counter
    print("Tokens in posts:", Counter(p.get("token_name") for p in posts))
except Exception as e:
    print("Err posts:", e)
