import urllib.request
import json
import re

url = "http://127.0.0.1:5080/"
try:
    resp = urllib.request.urlopen(url, timeout=5)
    html = resp.read().decode('utf-8', errors='replace')
    # Save to file
    with open("D:/Highlight_Video_Studio/web_test.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote web_test.html, length:", len(html))
    
    # Extract scripts
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    print("Found script tags:", len(scripts))
    for i, s in enumerate(scripts):
        with open(f"D:/Highlight_Video_Studio/script_{i}.js", "w", encoding="utf-8") as fs:
            fs.write(s)
        print(f"Script {i} length: {len(s)}")
except Exception as e:
    print("Error:", e)
