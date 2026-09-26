import requests
from bs4 import BeautifulSoup

r = requests.get("http://127.0.0.1:5080/")
print("HTTP status:", r.status_code)
print("Content length:", len(r.text))

# Let's inspect where index.html comes from
from pathlib import Path
for p in Path(r"D:\Highlight_Video_Studio").glob("**/index.html"):
    print(p, p.stat().st_size)
