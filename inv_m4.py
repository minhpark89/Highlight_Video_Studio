import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Boss says: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Let's check:
# 1. When boss searches/researches videos, what does boss click?
# Does boss click the video link or a button?
# Let's inspect research result cards:
idx = html.find('container.innerHTML = results.map')
if idx != -1:
    print("=== Research Card Code snippet ===")
    print(html[idx:idx+2500])

