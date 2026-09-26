with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos_t = text.find('id="pane-tokens"')
pos_end_t = text.find('</section>', pos_t)
with open('D:/Highlight_Video_Studio/extracted_pane_tokens.html', 'w', encoding='utf-8') as out:
    out.write(text[pos_t:pos_end_t+10])
print("Extracted pane-tokens, length:", pos_end_t - pos_t)
