from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect all getElementById in editGroupModal
pos = html.find('async function editGroupModal')
pos_end = html.find('function updateEditPageCount', pos)
js_code = html[pos:pos_end]
print("JS in editGroupModal:\n", js_code)

import re
ids_in_js = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", js_code)
print("\nIDs accessed in JS:", ids_in_js)

for el_id in ids_in_js:
    exists = f'id="{el_id}"' in html or f"id='{el_id}'" in html
    print(f"  {el_id}: exists in HTML? {exists}")
