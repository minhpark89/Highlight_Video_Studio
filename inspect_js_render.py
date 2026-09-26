import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

# Find loadTokensAndPages implementation completely
start = html.find('async function loadTokensAndPages()')
if start != -1:
    end = html.find('async function ', start + 30)
    if end == -1: end = start + 4000
    print("=== loadTokensAndPages ===")
    print(html[start:end])

# Check switchTab function
s_start = html.find('function switchTab(')
if s_start != -1:
    s_end = html.find('function ', s_start + 25)
    print("=== switchTab ===")
    print(html[s_start:s_end])

