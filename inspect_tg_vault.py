import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Let's inspect token_groups.json
tg_file = BASE_DIR / "token_groups.json"
if tg_file.exists():
    print("token_groups:", tg_file.read_text(encoding="utf-8"))
else:
    print("No token_groups.json")

# Let's inspect tokens_vault.json
tv_file = BASE_DIR / "tokens_vault.json"
if tv_file.exists():
    toks = json.loads(tv_file.read_text(encoding="utf-8"))
    print("Total tokens in vault:", len(toks))
