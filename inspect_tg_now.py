import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Let's inspect token_groups.json
tg_path = BASE_DIR / "token_groups.json"
tokens_path = BASE_DIR / "tokens_vault.json"

toks = json.loads(tokens_path.read_text(encoding="utf-8")) if tokens_path.exists() else []

# Check existing token_groups.json
if tg_path.exists():
    try:
        tgs = json.loads(tg_path.read_text(encoding="utf-8"))
    except Exception:
        tgs = []
else:
    tgs = []

print("Tokens count:", len(toks))
print("Current groups:", [g.get("name") for g in tgs])
