with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("def api_publish_reel")
print("=== api_publish_reel ===")
print(text[pos:pos+1500])
