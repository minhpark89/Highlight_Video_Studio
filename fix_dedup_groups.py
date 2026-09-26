import json
from pathlib import Path

# 1. Inspect page_groups.json
p = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
print("Current groups in page_groups.json:")
for g in groups:
    print(f"  ID: {g.get('id')} | Name: {g.get('name')} | Times: {g.get('schedule_config', {}).get('times')}")

# Deduplicate groups: keep group_bm1, and keep the latest 'nhóm 1' (ID: grp_1790349600_3 with times 22:35, 11:30)
cleaned = []
seen = set()
# Let's preserve unique group names, prioritizing the ones with schedule_config updated
for g in reversed(groups):
    name = g.get("name")
    if name not in seen:
        seen.add(name)
        cleaned.append(g)

cleaned.reverse()
p.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nDeduplicated groups count:", len(cleaned))
for g in cleaned:
    print(f"  Preserved ID: {g.get('id')} | Name: {g.get('name')}")
