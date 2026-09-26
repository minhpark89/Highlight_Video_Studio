import requests
import json

base_url = "http://127.0.0.1:5080"

# Check token groups
r_tg = requests.get(f"{base_url}/api/token-groups")
print("Token groups:", r_tg.status_code, r_tg.json())

# Check tokens
r_t = requests.get(f"{base_url}/api/tokens")
print("Tokens count:", len(r_t.json().get('tokens', [])))

# Check posts
r_p = requests.get(f"{base_url}/api/posts")
posts = r_p.json()
print("Posts count:", len(posts))
from collections import Counter
print("Tokens in posts:", Counter(p.get('token_name') for p in posts))
