with open('D:/Highlight_Video_Studio/web/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's check api_distribute_batch implementation detail
pos = text.find('def api_distribute_batch():')
if pos != -1:
    pos_end = text.find('\n@app.route', pos)
    print(text[pos:pos_end if pos_end != -1 else pos+3000])
