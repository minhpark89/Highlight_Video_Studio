import json

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's inspect pane-pages and pane-tokens and see how page groups are currently displayed
pos = html.find('id="pane-pages"')
pos_end = html.find('</section>', pos)
print("pane-pages snippet:")
print(html[pos:pos+2500])
