import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pos = html.find('id="sidebar"')
pos_end = html.find('</aside>', pos)
print("=== CURRENT SIDEBAR ===")
print(html[pos:pos_end+8])
