import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Check:
# 1. sendSelectedToStudio()
# 2. sendToRender()
# 3. Any button in research results

m1 = re.search(r'function sendSelectedToStudio\(\)\s*\{[\s\S]*?\n  \}', html)
print("=== sendSelectedToStudio ===")
if m1: print(m1.group(0))

m2 = re.search(r'function sendToRender\([^\)]*\)\s*\{[\s\S]*?\n  \}', html)
print("\n=== sendToRender ===")
if m2: print(m2.group(0))

