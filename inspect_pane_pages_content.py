with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos_p = text.find('id="pane-pages"')
if pos_p != -1:
    print("Found pane-pages at:", pos_p)
    # find where next pane starts
    pos_next = text.find('class="tab-pane', pos_p + 20)
    print("Next pane at:", pos_next)
    print("Length of pane-pages:", pos_next - pos_p if pos_next != -1 else len(text) - pos_p)
    print("Header of pane-pages:\n", text[pos_p:pos_p+800])
