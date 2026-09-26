with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos_sb = text.find('id="sidebar"')
pos_end_sb = text.find('</aside>', pos_sb)
print(text[pos_sb:pos_end_sb+8])
