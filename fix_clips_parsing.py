with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix clipsData handling in loadLoHaGroups
old_snip = "const clips = clipsData.clips || [];"
new_snip = "const clips = Array.isArray(clipsData) ? clipsData : (clipsData.clips || []);"

if old_snip in text:
    text = text.replace(old_snip, new_snip)
    print("Fixed clipsData parsing!")
    with open('D:/Highlight_Video_Studio/web/templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
else:
    print("old_snip not found")
