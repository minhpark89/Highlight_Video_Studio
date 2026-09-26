from pathlib import Path
import json

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect imports at the top of app.py
print("Top 40 lines of app.py:")
for l in text.splitlines()[:40]:
    print(l)
