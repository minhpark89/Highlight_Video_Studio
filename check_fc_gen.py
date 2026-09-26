from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect api_distribute_batch to see how the first comment was created
pos = app_text.find('def api_distribute_batch')
pos_end = app_text.find('@app.route', pos+10)
print(app_text[pos+1000:pos_end])
