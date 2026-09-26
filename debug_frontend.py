import urllib.request
import re

url = "http://127.0.0.1:5080/"
req = urllib.request.urlopen(url)
html = req.read().decode('utf-8')
print("HTML size:", len(html))

# Check where loadTokensAndPages is defined and called
print("Contains loadTokensAndPages:", "loadTokensAndPages" in html)

# Let's extract all JS in <script> tags
scripts = re.findall(r'<script.*?>([\s\S]*?)</script>', html, re.IGNORECASE)
print("Total scripts found:", len(scripts))

with open("D:/Highlight_Video_Studio/extracted_script.js", "w", encoding="utf-8") as f:
    for i, s in enumerate(scripts):
        f.write(f"\n/* --- SCRIPT {i} --- */\n")
        f.write(s)

print("Saved D:/Highlight_Video_Studio/extracted_script.js")
