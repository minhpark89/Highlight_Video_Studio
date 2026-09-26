import requests

res = requests.post("http://127.0.0.1:5080/api/posts/clear")
print("POST /api/posts/clear:", res.status_code, res.text[:300])

res2 = requests.post("http://127.0.0.1:5080/api/posts/clear", json={"status": "scheduled"})
print("POST with json:", res2.status_code, res2.text[:300])
