import requests

r = requests.post("http://127.0.0.1:5080/api/posts/clear", json={"status": "scheduled"})
print("Test /api/posts/clear:", r.status_code, r.json())
