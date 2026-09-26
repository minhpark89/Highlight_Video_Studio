import json, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
tokens_file = BASE_DIR / "tokens_vault.json"

shutil.copy2(tokens_file, tokens_file.with_suffix(".json.bak_34_tokens"))

with open(tokens_file, "r", encoding="utf-8") as f:
    tokens = json.load(f)

print(f"Initial tokens count: {len(tokens)}")

# Giữ lại các token 'autopost' (31 token thật của boss nạp), loại bỏ 3 'Token test'
cleaned_tokens = [t for t in tokens if t.get("name") != "Token test"]

# Đánh số hoặc đặt tên chuẩn LoHa AutoPool nếu cần
for idx, t in enumerate(cleaned_tokens, start=1):
    if t.get("name") == "autopost":
        t["name"] = f"AutoPool {idx:02d}"

with open(tokens_file, "w", encoding="utf-8") as f:
    json.dump(cleaned_tokens, f, ensure_ascii=False, indent=2)

print(f"Cleaned tokens count: {len(cleaned_tokens)} (Exactly 31 tokens!)")
for t in cleaned_tokens[:5]:
    print(" ", t.get("name"), t.get("status"), t.get("created_at"))
