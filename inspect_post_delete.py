from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = text.find('def api_delete_post')
print(text[pos:pos+1000])
