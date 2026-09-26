import requests
import json

base_url = "http://127.0.0.1:5080"

# Check groups
try:
    r = requests.get(f"{base_url}/api/groups")
    print("GET /api/groups:", r.status_code, len(r.json()))
except Exception as e:
    print("Error /api/groups:", e)

# Check posts
try:
    r = requests.get(f"{base_url}/api/posts")
    print("GET /api/posts:", r.status_code, len(r.json()))
except Exception as e:
    print("Error /api/posts:", e)

# Check clips
try:
    r = requests.get(f"{base_url}/api/clips")
    print("GET /api/clips:", r.status_code, "total clips:", len(r.json().get('clips', [])))
except Exception as e:
    print("Error /api/clips:", e)
