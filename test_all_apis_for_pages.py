import requests
from pathlib import Path

# 1. Test /api/pages
r = requests.get("http://127.0.0.1:5080/api/pages")
print("Status /api/pages:", r.status_code)
try:
    data = r.json()
    pages = data.get("pages", [])
    print("Total pages from API:", len(pages))
    if pages:
        print("First page sample:", pages[0].get("page_name"), pages[0].get("page_id"))
except Exception as e:
    print("Error parsing /api/pages:", e)

# 2. Test /api/tokens
r_tok = requests.get("http://127.0.0.1:5080/api/tokens")
print("Status /api/tokens:", r_tok.status_code)

# 3. Test /api/groups
r_grp = requests.get("http://127.0.0.1:5080/api/groups")
print("Status /api/groups:", r_grp.status_code)

# 4. Test /api/schedule/rules
r_rules = requests.get("http://127.0.0.1:5080/api/schedule/rules")
print("Status /api/schedule/rules:", r_rules.status_code)
