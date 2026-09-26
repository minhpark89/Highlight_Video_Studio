import requests

r = requests.get('http://127.0.0.1:5080/api/tokens')
print("Status:", r.status_code)
data = r.json()
print("Type:", type(data))
if isinstance(data, dict):
    print("Keys:", data.keys())
    print("Tokens count:", len(data.get('tokens', [])))
    if data.get('tokens'):
        print("Sample token:", data['tokens'][0])
