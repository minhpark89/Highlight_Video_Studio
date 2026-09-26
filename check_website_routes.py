with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("api_get_website_config")
if idx != -1:
    print(text[idx-50:idx+800])
