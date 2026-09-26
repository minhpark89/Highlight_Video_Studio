from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect api_distribute_batch
pos = text.find("def api_distribute_batch():")
sub = text[pos:pos+1600]
print(sub)
