import json
from pathlib import Path
import requests

tokens = json.loads(Path(r"D:\Highlight_Video_Studio\tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads(Path(r"D:\Highlight_Video_Studio\pages.json").read_text(encoding="utf-8"))

tok = tokens[0]["token"]
print("System User token len:", len(tok))

# Test 1: Can System User list accounts?
r_acc = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?access_token={tok}")
print("me/accounts status:", r_acc.status_code)
if r_acc.status_code == 200:
    data = r_acc.json().get("data", [])
    print(f"Total pages accessible by this token: {len(data)}")
    if data:
        print("First page from me/accounts:", data[0].get("name"), data[0].get("id"), "has access_token?", bool(data[0].get("access_token")))
else:
    print("me/accounts error:", r_acc.text[:300])

# Test 2: Can System User get page access token directly?
pid = pages[0]["page_id"]
r_page = requests.get(f"https://graph.facebook.com/v22.0/{pid}?fields=access_token,name&access_token={tok}")
print(f"Direct /{pid}?fields=access_token status:", r_page.status_code, r_page.text[:300])
