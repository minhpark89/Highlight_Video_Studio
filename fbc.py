import re, json

# Let's inspect web/templates/index.html around sendSelectedToStudio and the cards
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Let's see what happens when user clicks "Ném vào Cắt Highlight" vs "Ném vào Render"
# In sendSelectedToStudio:
idx = html.find('function sendSelectedToStudio')
print("sendSelectedToStudio definition:")
print(html[idx:idx+1200])

