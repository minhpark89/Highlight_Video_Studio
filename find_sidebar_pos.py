with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
pos_sidebar = text.find('id="sidebar"')
print("Sidebar index:", pos_sidebar)
print(text[pos_sidebar:pos_sidebar+1200])
