with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("def get_clips")
if idx != -1:
    print(text[idx-50:idx+800])
else:
    idx2 = text.find("/api/clips")
    print(text[idx2-50:idx2+800])
