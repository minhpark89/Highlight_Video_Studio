from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where page_manager is imported or where add_or_update_group is defined
for idx, line in enumerate(app_py.splitlines()[:60]):
    if "page_manager" in line or "PageManager" in line or "database" in line:
        print(f"{idx+1}: {line}")

pos = app_py.find("def api_save_group")
print("\n=== api_save_group ===\n", app_py[pos:pos+600])
