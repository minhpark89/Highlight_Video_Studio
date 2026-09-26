with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect /api/publish/reel or how posts are published
pos = text.find('api_publish_reel')
if pos != -1:
    print("=== api_publish_reel ===")
    print(text[pos:pos+1500])

# Check if there is /api/posts/run or auto publishing loop
pos_loop = text.find('def ')
matches = [m.start() for m in re.finditer(r'@app\.route\(.*publish|@app\.route\(.*schedule', text)]
for idx in matches:
    print(text[idx:idx+300])
