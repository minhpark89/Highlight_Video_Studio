import requests

r = requests.get('http://127.0.0.1:5080/api/groups')
print("Status:", r.status_code)
print("JSON:", r.json())
