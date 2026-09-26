import os
import json
import requests
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
PAGES_FILE = BASE_DIR / "pages.json"
TOKENS_FILE = BASE_DIR / "tokens_vault.json"

pages = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))

print(f"Total pages: {len(pages)}, total tokens: {len(tokens)}")

# Map token_id to SU token string
su_tokens_map = {t["id"]: t["token"] for t in tokens}
# Fallback list of SU tokens
su_tokens_list = [t["token"] for t in tokens if t.get("token")]

updated = 0
for idx, p in enumerate(pages):
    curr_token = p.get("access_token", "")
    # If already a valid page token that can access page, test it
    pid = p["page_id"]
    need_refresh = True
    if curr_token and len(curr_token) > 50:
        try:
            r = requests.get(f"https://graph.facebook.com/v22.0/{pid}?access_token={curr_token}", timeout=5)
            if r.status_code == 200:
                need_refresh = False
        except Exception:
            pass

    if need_refresh:
        # Get parent SU token
        tid = p.get("token_id")
        su_tok = su_tokens_map.get(tid)
        if not su_tok:
            su_tok = su_tokens_list[idx % len(su_tokens_list)]
        
        try:
            r_su = requests.get(f"https://graph.facebook.com/v22.0/{pid}?fields=access_token,name&access_token={su_tok}", timeout=5)
            if r_su.status_code == 200:
                p_tok = r_su.json().get("access_token")
                if p_tok:
                    p["access_token"] = p_tok
                    updated += 1
                    print(f"[{idx+1}/100] Refreshed Page Token for {p['page_name']} ({pid}) ✅")
            else:
                # Try finding across other SU tokens
                for alt_su in su_tokens_list:
                    r_alt = requests.get(f"https://graph.facebook.com/v22.0/{pid}?fields=access_token,name&access_token={alt_su}", timeout=5)
                    if r_alt.status_code == 200:
                        p["access_token"] = r_alt.json().get("access_token")
                        updated += 1
                        print(f"[{idx+1}/100] Found across SU Pool for {p['page_name']} ({pid}) ✅")
                        break
        except Exception as e:
            print(f"Error refreshing {pid}: {e}")

if updated > 0:
    PAGES_FILE.write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Successfully saved {updated} refreshed Page Access Tokens into pages.json!")
else:
    print("All page tokens already valid!")
