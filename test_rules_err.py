import requests
try:
    r = requests.get("http://127.0.0.1:5080/api/schedule/rules")
    print("rules status:", r.status_code)
    print("rules body:", r.text[:400])
except Exception as e:
    print("rules request error:", e)
