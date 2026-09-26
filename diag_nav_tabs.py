import urllib.request
from bs4 import BeautifulSoup
import re

url = "http://127.0.0.1:5080/"
html = urllib.request.urlopen(url).read().decode("utf-8")

# Let's inspect the navigation buttons in HTML
nav_btns = re.findall(r'<button[^>]*class=["\'][^"\']*nav-btn[^"\']*["\'][^>]*>[\s\S]*?</button>', html)
print(f"Total nav buttons found in served HTML: {len(nav_btns)}")
for b in nav_btns:
    print("--- BTN ---")
    print(b)

# Check all panes
panes = re.findall(r'<section[^>]*id=["\'](pane-[a-zA-Z0-9_\-]+)["\'][^>]*>', html)
print(f"Panes found: {panes}")

# Check switchTab function in served HTML
pos = html.find("window.switchTab")
if pos != -1:
    print("switchTab definition snippet:")
    print(html[pos:pos+1500])
else:
    print("window.switchTab NOT FOUND!")
