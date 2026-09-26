import requests

r = requests.get('http://127.0.0.1:5080/api/token-groups')
print("Status:", r.status_code)
print("Data:", r.json())
