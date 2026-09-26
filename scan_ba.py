with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Let's inspect sendSelectedToStudio vs sendToRender
import re
print("--- sendSelectedToStudio ---")
m1 = re.search(r'function sendSelectedToStudio\(\)\s*\{[\s\S]*?\n  \}', html)
if m1:
    print(m1.group(0))

print("\n--- sendToRender ---")
m2 = re.search(r'function sendToRender\([^\)]*\)\s*\{[\s\S]*?\n  \}', html)
if m2:
    print(m2.group(0))

print("\n--- Buttons rendered in research results ---")
idx = html.find('container.innerHTML = results.map')
if idx != -1:
    print(html[idx:idx+2500])

