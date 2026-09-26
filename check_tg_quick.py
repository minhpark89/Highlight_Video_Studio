import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Let's inspect token_groups.json
tg_path = BASE_DIR / "token_groups.json"
print("token_groups content:")
print(tg_path.read_text(encoding="utf-8") if tg_path.exists() else "None")

# Let's inspect tokens_vault.json
tv_path = BASE_DIR / "tokens_vault.json"
toks = json.loads(tv_path.read_text(encoding="utf-8")) if tv_path.exists() else []
print("Total tokens in vault:", len(toks))
