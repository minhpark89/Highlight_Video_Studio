from pathlib import Path

# Let's inspect src/database/page_manager.py or wherever page_manager is
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*page*manager*.py"):
    txt = p.read_text(encoding="utf-8")
    print(f"=== {p} ===")
    lines = txt.splitlines()
    for idx, l in enumerate(lines):
        if "def add_or_update_group" in l or "def save_group" in l:
            for j in range(idx, min(len(lines), idx+30)):
                print(f"{j+1}: {lines[j]}")
