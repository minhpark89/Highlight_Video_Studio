import requests
import json
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))

p0 = pages[0]
pid = p0["page_id"]
pname = p0["page_name"]
print(f"Target Page: {pname} ({pid})")

# Let's find which token in tokens_vault has this page in /me/accounts
found_token = None
found_page_token = None

for t in tokens:
    tok = t.get("token")
    try:
        r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={tok}", timeout=5)
        if r.status_code == 200:
            for acc in r.json().get("data", []):
                if acc.get("id") == pid:
                    found_token = t
                    found_page_token = acc.get("access_token")
                    print(f"MATCH FOUND in Token {t.get('name')}!")
                    print(f"Page Access Token: {found_page_token[:30]}...")
                    print(f"Tasks: {acc.get('tasks')}")
                    break
        if found_token:
            break
    except Exception as e:
        pass

if not found_token:
    print(f"Page {pid} was not found in any of the {len(tokens)} tokens in tokens_vault!")
    # Let's see what pages ARE in token 1
    r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=10&access_token={tokens[0]['token']}")
    print("Sample pages in Token 1:", [(x.get('id'), x.get('name')) for x in r.json().get('data', [])])
