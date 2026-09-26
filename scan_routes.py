import re
import json

with open('D:/Highlight_Video_Studio/web/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

routes = re.findall(r'@app\.route\((.*?)\)', code)
print(f"Total routes: {len(routes)}")
for r in routes:
    if any(k in r for k in ['distribute', 'post', 'group', 'token', 'clip', 'purge', 'page', 'website']):
        print("ROUTE:", r.strip())
