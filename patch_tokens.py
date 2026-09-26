import re

path = 'D:/Highlight_Video_Studio/web/app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change total_pages_synced initialization
content = content.replace("total_pages_synced = 0", "synced_page_ids = set()", 1)

# 2. Change sync loop addition
old_sync = """            if pages:
                page_manager.sync_pages_from_token(entry, pages)
                total_pages_synced += len(pages)"""

new_sync = """            if pages:
                page_manager.sync_pages_from_token(entry, pages)
                for p in pages:
                    pid = p.get("id") or p.get("page_id")
                    if pid:
                        synced_page_ids.add(str(pid))"""

content = content.replace(old_sync, new_sync, 1)

# 3. Change response
content = content.replace('"synced_pages": total_pages_synced,', '"synced_pages": len(synced_page_ids),', 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS_PATCHED_APP_PY")
