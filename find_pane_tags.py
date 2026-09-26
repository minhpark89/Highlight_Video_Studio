with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# check how panes are declared
for match in re.finditer(r'id=["\']pane-[^"\']+["\']', text):
    start = max(0, match.start() - 30)
    end = min(len(text), match.end() + 30)
    print(text[start:end])
