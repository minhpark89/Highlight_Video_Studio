with open("D:/Highlight_Video_Studio/web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("WEBSITE ARTICLE CMS CONFIG")
if idx != -1:
    print(text[idx:idx+800])
else:
    print("Not found in web/index.html")
