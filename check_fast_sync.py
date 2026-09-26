import re

with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

# Let's see how sync_pages_from_token works
with open(r'D:\Highlight_Video_Studio\src\publisher\page_manager.py', 'r', encoding='utf-8') as f:
    pm_text = f.read()

print("PAGE_MANAGER sync_pages_from_token:")
idx = pm_text.find("def sync_pages_from_token")
if idx != -1:
    print(pm_text[idx:idx+1200])

