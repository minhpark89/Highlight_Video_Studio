# Check all files in D:\Highlight_Video_Studio to see what could trigger CMD
import os, glob

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's search for every button on the page that could be related to render or links:
import re
print("--- Searching for any handler that opens links or windows ---")
for m in re.finditer(r'<button[^>]*>([\s\S]*?)<\/button>', text):
    btn_html = m.group(0)
    if any(k in btn_html.lower() for k in ['render', 'cắt', 'highlight', 'ném']):
        print(btn_html.replace('\n', ' ')[:150])

