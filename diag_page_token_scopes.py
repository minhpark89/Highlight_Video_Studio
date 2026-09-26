import requests
import json
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))

su_token = tokens[0]["token"]
p = pages[0]
pid = p["page_id"]

# Get page access token
r = requests.get(f"https://graph.facebook.com/v22.0/{pid}?fields=access_token,name,roles&access_token={su_token}")
page_token = r.json().get("access_token")

# Debug page token
r_dbg = requests.get(f"https://graph.facebook.com/debug_token?input_token={page_token}&access_token={su_token}")
print("Page Token Debug:", json.dumps(r_dbg.json(), indent=2))
