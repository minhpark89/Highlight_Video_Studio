import os, re

# Search across all html and js files on D: for where window.open or cmd might be invoked
for base in [r"D:\Highlight_Video_Studio", r"D:\News_Video_Studio", r"D:\FB_Longform_Studio"]:
    if not os.path.exists(base): continue
    for root, dirs, files in os.walk(base):
        if any(x in root for x in [".git", "venv", "__pycache__", "downloads"]): continue
        for f in files:
            if f.endswith(('.html', '.js')):
                p = os.path.join(root, f)
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                # Check for buttons or clicks that trigger window.open, cmd, or render
                for m in re.finditer(r'(window\.open|exec|cmd\.exe|renderVideo|startRender|sendToRender)', content):
                    start = max(0, m.start() - 40)
                    end = min(len(content), m.end() + 60)
                    print(f"[{os.path.relpath(p, base)}] {content[start:end].replace(chr(10), ' ')}")

