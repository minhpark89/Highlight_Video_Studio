import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

# 1. Search for renderPagesTable or how pages are rendered
idx = html.find('loadTokensAndPages')
print("Snippet of loadTokensAndPages:\n", html[idx:idx+2500])

