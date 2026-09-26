with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
sb_pos = text.find('id="sidebar"')
sb_end = text.find('</aside>', sb_pos)
print("=== SIDEBAR ===")
print(text[sb_pos:sb_end+8])
