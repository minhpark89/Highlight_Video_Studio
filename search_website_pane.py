with open("D:/Highlight_Video_Studio/web/templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("pane-website")
while idx != -1:
    print(text[idx-50:idx+250])
    print("="*40)
    idx = text.find("pane-website", idx + 1)
