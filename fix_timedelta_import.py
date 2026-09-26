from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Check imports
if "from datetime import datetime, timedelta" not in text:
    if "from datetime import datetime" in text:
        text = text.replace("from datetime import datetime", "from datetime import datetime, timedelta", 1)
        print("Replaced datetime import with timedelta!")
    else:
        text = "from datetime import datetime, timedelta\n" + text
        print("Prepended datetime and timedelta import!")

app_path.write_text(text, encoding="utf-8")
print("Saved app.py!")
