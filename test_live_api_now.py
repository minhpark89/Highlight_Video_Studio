import requests

# Test /api/groups
r_g = requests.get('http://127.0.0.1:5080/api/groups')
print("Groups status:", r_g.status_code)
print("Groups data:", r_g.json())

# Test /api/tokens
r_t = requests.get('http://127.0.0.1:5080/api/tokens')
print("Tokens status:", r_t.status_code)
print("Tokens count:", len(r_t.json().get('tokens', [])))
