from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect how token is retrieved for a post in api_distribute_batch
pos = app_text.find('def api_distribute_batch')
pos_end = app_text.find('save_posts(posts)', pos)
print(app_text[pos+1000:pos_end+30])
