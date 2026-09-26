import requests

# Let's test the 4 endpoints that loadTokensAndPages calls:
endpoints = [
    '/api/tokens',
    '/api/pages',
    '/api/groups',
    '/api/schedule/rules'
]

for ep in endpoints:
    try:
        r = requests.get(f"http://127.0.0.1:5080{ep}")
        print(f"{ep}: status={r.status_code}")
        if r.status_code != 200:
            print(f"  Error body: {r.text[:300]}")
    except Exception as e:
        print(f"{ep}: exception={e}")
