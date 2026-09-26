with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'pane-tokens', text)]
print("Matches for pane-tokens:", len(matches))
for pos in matches:
    start = max(0, pos - 40)
    end = min(len(text), pos + 80)
    print(text[start:end])
    print("---")
