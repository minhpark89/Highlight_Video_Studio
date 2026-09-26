import json
import requests
from pathlib import Path

pages = json.loads(Path(r"D:\Highlight_Video_Studio\pages.json").read_text(encoding="utf-8"))
tokens = json.loads(Path(r"D:\Highlight_Video_Studio\tokens_vault.json").read_text(encoding="utf-8"))

su_token = tokens[0]["token"]
p = pages[0]
pid = p["page_id"]

print(f"Testing Page {p['page_name']} ({pid}) with SU token...")
r = requests.get(f"https://graph.facebook.com/v22.0/{pid}?fields=access_token,name&access_token={su_token}")
print("Response:", r.status_code, r.json())
page_access_token = r.json().get("access_token")
print("Got Page Access Token len:", len(page_access_token))

# Now test what permissions this page token has
r_test = requests.get(f"https://graph.facebook.com/v22.0/{pid}?access_token={page_access_token}")
print("Test with Page Token:", r_test.status_code, r_test.text)
