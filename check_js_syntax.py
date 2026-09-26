import subprocess
import urllib.request
import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
print(f"Total script blocks: {len(scripts)}")
for i, s in enumerate(scripts):
    with open(f"D:/Highlight_Video_Studio/temp_script_{i}.js", "w", encoding="utf-8") as fs:
        fs.write(s)
    res = subprocess.run(["node", "--check", f"D:/Highlight_Video_Studio/temp_script_{i}.js"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Script {i} ERROR:\n", res.stderr)
    else:
        print(f"Script {i} syntax OK! ({len(s)} bytes)")
