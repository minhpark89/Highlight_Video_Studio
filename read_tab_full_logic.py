with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

import re
# Check switchTab
idx = text.find('function switchTab(')
print("=== switchTab ===")
print(text[idx:idx+600])

# Check loadTokensAndPages
idx2 = text.find('async function loadTokensAndPages()')
print("=== loadTokensAndPages ===")
print(text[idx2:idx2+1200])

