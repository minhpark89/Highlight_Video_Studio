import json
from pathlib import Path

vault_path = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")
tokens = json.loads(vault_path.read_text(encoding="utf-8"))
print("Total tokens in vault:", len(tokens))

for idx, t in enumerate(tokens[:5]):
    tok_str = t.get("token", "")
    print(f"Token {idx+1} ({t.get('name')}): prefix={tok_str[:25]}... suffix={tok_str[-15:]} len={len(tok_str)}")
