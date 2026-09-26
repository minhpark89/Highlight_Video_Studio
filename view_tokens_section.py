with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos_t = text.find('id="pane-tokens"')
pos_end_t = text.find('</section>', pos_t)
print("=== PANE-TOKENS CONTENT ===")
print(text[pos_t:pos_end_t+10])
