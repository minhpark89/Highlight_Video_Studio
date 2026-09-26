with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Let's inspect switchTab function
idx = text.find('function switchTab(')
print("switchTab snippet:")
print(text[idx:idx+800])

