with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Let's inspect play_clip and see where we can add delete / mark posted
idx = code.find("def play_clip(filename):")
print(code[idx-50:idx+600])
