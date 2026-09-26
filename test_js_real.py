with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', text, re.DOTALL)
print(f"Total script blocks in index.html: {len(scripts)}")
for i, s in enumerate(scripts):
    with open(f"D:/Highlight_Video_Studio/temp_script_{i}.js", "w", encoding="utf-8") as fs:
        fs.write(s)
    import subprocess
    r = subprocess.run(["node", "--check", f"D:/Highlight_Video_Studio/temp_script_{i}.js"], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"SCRIPT {i} SYNTAX ERROR:\n", r.stderr)
    else:
        print(f"Script {i} syntax OK! Size: {len(s)}")
