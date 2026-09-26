import re

for filepath in [r'D:\Highlight_Video_Studio\web\app.py', r'D:\Highlight_Video_Studio\src\pipeline.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"=== {filepath} ===")
    matches = re.findall(r'def [^\n]*jobs[^\n]*\([^)]*\):.*?(?=\ndef |\Z)', content, re.DOTALL)
    for m in matches:
        print(m[:400])
        print("-" * 30)

