import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's inspect where video cards in research results are generated:
idx = text.find('container.innerHTML = results.map')
if idx != -1:
    print(text[idx:idx+2500])

