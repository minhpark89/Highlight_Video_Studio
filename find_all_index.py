import requests
from pathlib import Path

r = requests.get("http://127.0.0.1:5080/")
print("Live response length:", len(r.text))

# Let's search where in r.text
print("Has modal-edit-group?", "modal-edit-group" in r.text)

# Let's inspect D:\Highlight_Video_Studio to see all index.html files
for p in Path(r"D:\Highlight_Video_Studio").glob("**/index.html"):
    print(p, p.stat().st_size)
