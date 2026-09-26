with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# check all sections
sections = re.findall(r'<section\s+id="([^"]+)"[^>]*>', text)
print("Sections:", sections)
