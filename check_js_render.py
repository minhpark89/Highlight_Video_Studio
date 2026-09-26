import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

# Find loadTokensAndPages definition
idx = html.find('async function loadTokensAndPages')
if idx != -1:
    print("Found loadTokensAndPages at", idx)
    print(html[idx:idx+1500])
else:
    print("loadTokensAndPages NOT FOUND")
