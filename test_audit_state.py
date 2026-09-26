import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
print("Base dir exists:", BASE_DIR.exists())

# Check output dir
out_dir = BASE_DIR / "output"
mp4s = list(out_dir.glob("*.mp4"))
print(f"Total mp4s in output: {len(mp4s)}")
if mp4s:
    print("Sample mp4:", mp4s[0].name)

# Check pages.json
pages_file = BASE_DIR / "pages.json"
if pages_file.exists():
    pages = json.loads(pages_file.read_text(encoding="utf-8"))
    print(f"Total pages: {len(pages)}")
    if pages:
        print("Sample page:", pages[0].get("page_name"), "| ID:", pages[0].get("page_id"), "| Token:", pages[0].get("token_name"))

# Check page_groups.json
groups_file = BASE_DIR / "page_groups.json"
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print(f"Total groups: {len(groups)}")
    for g in groups:
        print("Group:", g.get("name"), "| pages:", len(g.get("page_ids", [])))

# Check tokens_vault.json
tokens_file = BASE_DIR / "tokens_vault.json"
if tokens_file.exists():
    tokens = json.loads(tokens_file.read_text(encoding="utf-8"))
    print(f"Total tokens in vault: {len(tokens)}")
