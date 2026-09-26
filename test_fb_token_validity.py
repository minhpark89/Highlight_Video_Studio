import json
from pathlib import Path

tokens = json.loads(Path(r"D:\Highlight_Video_Studio\tokens_vault.json").read_text(encoding="utf-8"))
tok_test = tokens[0]["token"]
print("Testing token 1 length:", len(tok_test))

import requests
# Test debug_token
r = requests.get(f"https://graph.facebook.com/debug_token?input_token={tok_test}&access_token={tok_test}")
print("debug_token status:", r.status_code)
print("debug_token text:", r.text[:300])

r_me = requests.get(f"https://graph.facebook.com/v22.0/me?access_token={tok_test}")
print("me status:", r_me.status_code)
print("me text:", r_me.text[:300])
