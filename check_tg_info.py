import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Read tokens_vault.json
tv_file = BASE_DIR / "tokens_vault.json"
toks = json.loads(tv_file.read_text(encoding="utf-8")) if tv_file.exists() else []

# Read token_groups.json
tg_file = BASE_DIR / "token_groups.json"
tgs = json.loads(tg_file.read_text(encoding="utf-8")) if tg_file.exists() else []

print("Total tokens in vault:", len(toks))
print("Total token groups:", len(tgs))
for g in tgs:
    print("Group:", g.get("name"), "tokens count:", len(g.get("token_ids", [])))
