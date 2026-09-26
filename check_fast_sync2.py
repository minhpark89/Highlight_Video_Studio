import re

with open(r'D:\Highlight_Video_Studio\src\publisher\page_manager.py', 'r', encoding='utf-8') as f:
    text = f.read()

print("PAGE_MANAGER len:", len(text))
# Find functions in PageManager
funcs = re.findall(r'def\s+(\w+)\s*\(', text)
print("Funcs:", funcs)

