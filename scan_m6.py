import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Let's inspect:
# 1. Research pane: when research completes, how are links rendered?
# What HTML is created for each video card?
# Let's print out the exact string returned in results.map
idx = html.find('container.innerHTML = results.map')
if idx != -1:
    print("=== MAP FUNCTION ===")
    print(html[idx:idx+2500])

