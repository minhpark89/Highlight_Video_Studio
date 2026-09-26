from pathlib import Path

pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")
tokens_file = Path(r"D:\Highlight_Video_Studio\tokens_vault.json")

import json

pages = json.loads(pages_file.read_text(encoding="utf-8"))
tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

print(f"Total pages: {len(pages)}, Total tokens: {len(tokens)}")

# Distribute 31 tokens evenly across 100 pages
# 100 pages / 31 tokens ~= 3-4 pages per token
for i, p in enumerate(pages):
    tok = tokens[i % len(tokens)]
    p["token_id"] = tok.get("id")
    p["token_name"] = tok.get("name")

pages_file.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
print("Successfully distributed 31 tokens evenly across 100 pages!")

# Verify distribution
from collections import Counter
c = Counter(p.get("token_name") for p in pages)
print("Distribution sample:", list(c.items())[:5])
