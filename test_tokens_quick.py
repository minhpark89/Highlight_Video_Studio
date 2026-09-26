import json
from pathlib import Path

vault_path = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")
tokens = json.loads(vault_path.read_text(encoding="utf-8"))

print("Testing first 5 tokens:")
import requests
for t in tokens[:5]:
    tok = t["token"]
    r = requests.get(f"https://graph.facebook.com/v22.0/me?access_token={tok}")
    print(f"{t['name']}: code={r.status_code}, resp={r.text[:120]}")
