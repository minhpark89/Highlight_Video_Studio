import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Let's inspect token_groups.json
tg_file = BASE_DIR / "token_groups.json"
if tg_file.exists():
    print("token_groups:", tg_file.read_text(encoding="utf-8"))

# Let's inspect tokens_vault.json
tokens_file = BASE_DIR / "tokens_vault.json"
if tokens_file.exists():
    tokens = json.loads(tokens_file.read_text(encoding="utf-8"))
    print("Tokens count:", len(tokens))

# Check app.py routes for token-groups
with open(BASE_DIR / "web" / "app.py", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('api_get_token_groups')
if pos == -1: pos = text.find('/api/token-groups')
print("token-groups route in app.py:")
print(text[pos:pos+600])
