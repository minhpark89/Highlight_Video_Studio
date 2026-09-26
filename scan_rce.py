import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Boss says: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Let's check:
# 1. Did boss click on the title link <a href="..."> of the 3 videos or thumbnail?
# 2. Or did boss click on "Ném vào Render" button on each of the 3 cards?
# Let's inspect the exact HTML of the card in research results:

idx = html.find('container.innerHTML = results.map')
if idx != -1:
    print(html[idx:idx+2500])

