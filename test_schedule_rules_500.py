import requests

r = requests.get("http://127.0.0.1:5080/api/schedule/rules")
print("Status:", r.status_code)
print("Response text:", r.text[:500])
