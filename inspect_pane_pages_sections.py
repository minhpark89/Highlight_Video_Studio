import json
import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect pane-pages to see what sections exist inside it
pos_p = text.find('id="pane-pages"')
if pos_p != -1:
    sub = text[pos_p:pos_p+15000]
    # find any buttons or tabs or sections
    headers = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', sub)
    print("Headers in pane-pages:", headers)
