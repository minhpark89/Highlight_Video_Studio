import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
with open(BASE_DIR / "web" / "app.py", "r", encoding="utf-8") as f:
    text = f.read()

pos1 = text.find('def api_add_group')
if pos1 == -1:
    pos1 = text.find('/api/groups", methods=["POST"]')
print("api_add_group:")
print(text[pos1:pos1+800])

pos2 = text.find('def api_delete_group')
print("\napi_delete_group:")
print(text[pos2:pos2+600])
