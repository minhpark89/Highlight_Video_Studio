from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where first comment is formatted in api_distribute_batch
pos = app_text.find('def api_distribute_batch')
pos_end = app_text.find('@app.route', pos+10)
snippet = app_text[pos:pos_end]

for line in snippet.splitlines():
    if 'first_comment' in line or 'Xem trọn' in line or 'comment' in line:
        print(line)
