with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
sidebar_match = re.search(r'(<nav\s+class="sidebar-nav".*?</nav>)', html, re.DOTALL)
if not sidebar_match:
    sidebar_match = re.search(r'(<div\s+id="sidebar".*?</div>\s*<!-- /sidebar -->)', html, re.DOTALL)

# Let's search for sidebar content
pos = html.find('id="sidebar"')
if pos != -1:
    print("Found #sidebar around:", pos)
    print(html[pos:pos+3000])
else:
    print("No #sidebar found")
