import requests

res = requests.post("http://127.0.0.1:5080/api/posts/clear", json={"status": "scheduled"})
print("Status code:", res.status_code)
print("Response text:", res.text)
