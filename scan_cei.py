import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Boss says: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Let's see:
# 1. Did boss click on:
# a) Checkboxes?
# b) The video card's buttons or links?
# Look at the card template:
# <a href="${v.url}" target="_blank" class="clip-title" ...>
# <button onclick="sendToRender('${v.url}')">
# <button onclick="openVideoPlayerModal(...)">
# <button onclick="copyVideoUrl(...)">

# Why would "3 tab cmd đen hiện ra"?
# Is there ANY code that opens CMD or runs a command?
# What about D:\News_Video_Studio or other studios?
print("=== Let's inspect D:\\News_Video_Studio vs D:\\Highlight_Video_Studio ===")

