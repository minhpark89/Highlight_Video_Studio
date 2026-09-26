import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Let's inspect the entire research results rendering:
# Look for where video cards are generated and where the links are
idx = html.find('container.innerHTML = results.map')
if idx != -1:
    print("=== MAP SNIPPET ===")
    print(html[idx:idx+2500])

