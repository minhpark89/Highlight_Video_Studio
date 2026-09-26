with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect the robust switcher in <head>
pos_s = text.find('window.switchTab = function')
if pos_s != -1:
    print(text[pos_s:pos_s+1000])
else:
    print("switchTab definition not found by string")
