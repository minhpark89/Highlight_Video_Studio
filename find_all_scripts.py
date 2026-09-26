with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print("Total script blocks:", len(scripts))
for i, s in enumerate(scripts):
    print(f"Script #{i}: length {len(s)}")
    # Find any function definition
    fns = re.findall(r'function\s+([a-zA-Z0-9_$]+)\s*\(', s)
    if fns:
        print("  Functions:", fns[:8])
    if 'pages' in s.lower() or 'token' in s.lower():
        print("  Mentions pages/token")
