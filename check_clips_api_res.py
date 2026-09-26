import requests

r = requests.get('http://127.0.0.1:5080/api/clips')
print("Status:", r.status_code)
data = r.json()
print("Type:", type(data))
if isinstance(data, list):
    print("List length:", len(data))
    if data:
        print("Item 0:", data[0])
elif isinstance(data, dict):
    print("Keys:", data.keys())
