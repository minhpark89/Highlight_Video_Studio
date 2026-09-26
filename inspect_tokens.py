import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
NVS_DIR = Path(r"D:\News_Video_Studio")

# 1. Inspect tokens in vault
with open(BASE_DIR / "tokens_vault.json", "r", encoding="utf-8") as f:
    vault_tokens = json.load(f)

print("HVS vault tokens count:", len(vault_tokens))

# Check NVS meta_app_tokens.json
nvs_tokens_file = NVS_DIR / "data" / "registry" / "meta_app_tokens.json"
if nvs_tokens_file.exists():
    with open(nvs_tokens_file, "r", encoding="utf-8") as f:
        nvs_tokens = json.load(f)
    print("NVS meta_app_tokens count:", len(nvs_tokens))
    for t in nvs_tokens[:5]:
        print(" NVS token:", t.get("name") or t.get("app_id"), t.get("status"))

for idx, t in enumerate(vault_tokens):
    print(f"{idx+1}: name={t.get('name')} kind={t.get('kind')} status={t.get('status')} created={t.get('created_at')}")
