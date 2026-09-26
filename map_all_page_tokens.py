import json
import requests
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
PAGES_FILE = BASE_DIR / "pages.json"
TOKENS_FILE = BASE_DIR / "tokens_vault.json"

pages = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))

print(f"Scanning all {len(tokens)} System User tokens for {len(pages)} pages...")

page_token_catalog = {} # pid -> { 'page_token': ..., 'su_token_id': ..., 'su_token_name': ..., 'tasks': ... }

for idx, t in enumerate(tokens):
    tok = t.get("token")
    tid = t.get("id")
    tname = t.get("name")
    try:
        r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={tok}", timeout=8)
        if r.status_code == 200:
            accs = r.json().get("data", [])
            for acc in accs:
                pid = acc.get("id")
                ptok = acc.get("access_token")
                tasks = acc.get("tasks", [])
                if pid and ptok and ("CREATE_CONTENT" in tasks or len(tasks) > 0):
                    page_token_catalog[pid] = {
                        "access_token": ptok,
                        "token_id": tid,
                        "token_name": tname,
                        "tasks": tasks
                    }
        print(f"Token {idx+1}/{len(tokens)} ({tname}): accounts={len(page_token_catalog)}")
    except Exception as e:
        print(f"Token {tname} error:", e)

print(f"\nTotal unique pages matched with real Page Access Tokens: {len(page_token_catalog)}")

# Update pages.json with the real Page Access Tokens
matched = 0
for p in pages:
    pid = p.get("page_id")
    if pid in page_token_catalog:
        p["access_token"] = page_token_catalog[pid]["access_token"]
        p["token_id"] = page_token_catalog[pid]["token_id"]
        p["token_name"] = page_token_catalog[pid]["token_name"]
        matched += 1

PAGES_FILE.write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved {matched} real Page Access Tokens into pages.json!")
