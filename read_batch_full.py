from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_text.find('def api_distribute_batch')
pos_end = app_text.find('save_posts(posts)', pos)
print(app_text[pos:pos_end+30])
