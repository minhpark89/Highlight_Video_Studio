from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search for delete post route
pos = text.find('api_delete_post')
if pos != -1:
    print(text[pos:pos+600])
else:
    print("api_delete_post not found")
