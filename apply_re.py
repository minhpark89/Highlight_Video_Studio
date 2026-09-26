from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Add import re at line 1
text = "import re\n" + text
app_path.write_text(text, encoding="utf-8")
print("Saved app.py with import re!")
