import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect switchTab logic in head
pos_sw = text.find('window.switchTab = function')
print("switchTab found at:", pos_sw)
if pos_sw != -1:
    print(text[pos_sw:pos_sw+600])

# Let's inspect where nav buttons are
pos_nav = text.find('class="nav-group"')
print("nav-group found at:", pos_nav)
if pos_nav != -1:
    print(text[pos_nav:pos_nav+1200])
