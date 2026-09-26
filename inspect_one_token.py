import json
from pathlib import Path

vault_path = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")
tokens = json.loads(vault_path.read_text(encoding="utf-8"))

# Print first token full
print("Token 1 name:", tokens[0].get("name"))
print("Token 1 token:", tokens[0].get("token"))
