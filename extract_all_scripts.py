import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Total script tags: {len(scripts)}")
for i, s in enumerate(scripts):
    fname = f"D:/Highlight_Video_Studio/temp_script_{i}.js"
    with open(fname, 'w', encoding='utf-8') as out:
        out.write(s)
    print(f"Wrote {fname} (length {len(s)})")
