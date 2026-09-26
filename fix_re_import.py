from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Check imports in app.py
if "import re\n" not in text:
    text = "import re\n" + text
    print("Added import re to top of app.py!")

app_path.write_text(text, encoding="utf-8")
print("Saved app.py with re import!")
