with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'<div[^>]+id=[\"\']pane-[^\"\']+[\"\'][^>]*>', text)
print("Divs with id=pane-:")
for m in matches:
    print(m)
