with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

idx = html.find('async function loadTokensAndPages()')
print(html[idx:idx+4500])
