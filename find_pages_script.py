import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect pane-pages script logic to see how pages and groups are loaded
pos_script = text.find('// Page Manager & LoHa Logic')
if pos_script == -1:
    pos_script = text.find('loadPages(')
print("pos_script:", pos_script)
if pos_script != -1:
    print(text[pos_script-100:pos_script+1200])
