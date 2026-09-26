import urllib.request
import re

html = urllib.request.urlopen("http://127.0.0.1:5080/").read().decode("utf-8")

# Check all button onclicks in sidebar
buttons = re.findall(r'<button[^>]*class=["\'][^"\']*nav-btn[^"\']*["\'][^>]*>', html)
for b in buttons:
    print(b)
