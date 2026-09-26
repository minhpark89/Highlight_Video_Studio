import re

with open(r'D:\News_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    news_html = f.read()

# Check what happens when clicking render buttons in News_Video_Studio
for m in re.finditer(r'<button[^>]*onclick="([^"]*)"[^>]*>([\s\S]*?)<\/button>', news_html):
    oc = m.group(1)
    txt = m.group(2).strip().replace('\n', ' ')
    if any(k in txt.lower() or k in oc.lower() for k in ['render', 'cào', 'crawl', 'cmd', 'link']):
        print(f"NEWS: [{txt[:40]}] -> onclick='{oc}'")

