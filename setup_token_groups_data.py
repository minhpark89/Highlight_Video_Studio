import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Check token_groups.json
tg_path = BASE_DIR / "token_groups.json"
tokens_path = BASE_DIR / "tokens_vault.json"

tokens = json.loads(tokens_path.read_text(encoding="utf-8")) if tokens_path.exists() else []

# Create / update token_groups.json with default groups
# e.g., "Nhóm AutoPool Chính (31 Token)" containing all 31 token IDs, and "BM 1 (Pool 1)"
all_token_ids = [t.get("id") for t in tokens]

groups = [
    {
        "id": "tg_autopool_main",
        "name": "Nhóm AutoPool Chính",
        "description": "Toàn bộ 31 Token System User xoay vòng chịu tải",
        "strategy": "least_recently_used",
        "max_threads": 10,
        "token_ids": all_token_ids,
        "created_at": "2026-09-24 20:00:00"
    },
    {
        "id": "tg_bm1",
        "name": "BM 1 (Pool 1)",
        "description": "Nhóm 10 Token đầu cho dàn Page chính",
        "strategy": "least_recently_used",
        "max_threads": 5,
        "token_ids": all_token_ids[:10],
        "created_at": "2026-09-25 15:00:00"
    }
]

tg_path.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved token_groups.json with 2 groups!")
