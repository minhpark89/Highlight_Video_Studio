import requests
import json
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))

su_token = tokens[0]["token"]
print("SU token prefix:", su_token[:25])

# Let's inspect token debug info
r = requests.get(f"https://graph.facebook.com/debug_token?input_token={su_token}&access_token={su_token}")
print("Token debug:", r.json())
