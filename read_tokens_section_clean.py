with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)
print("=== PANE-TOKENS SLICE ===")
print(html[pos_t:pos_end_t+10])
