with open("D:/Highlight_Video_Studio/web/templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find('id="pane-website"')
print(text[idx:idx+2000])
