import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Check what happens in index.html around sendSelectedToStudio and buttons
for fn in ['sendSelectedToStudio', 'sendToRender', 'openVideoPlayerModal']:
    m = re.search(r'function\s+' + fn + r'\s*\([^)]*\)\s*\{[\s\S]*?\n  \}', html)
    if m:
        print(f"=== {fn} ===")
        print(m.group(0)[:1200])

