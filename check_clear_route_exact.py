from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = text.find('api_clear_posts')
print(text[pos-100:pos+400])
