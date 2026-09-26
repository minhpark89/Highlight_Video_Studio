from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is defined
pos = text.find("def api_distribute_batch():")
print("Position:", pos)
if pos != -1:
    print(text[pos:pos+1500])
