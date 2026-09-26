import re

# Inspect all buttons in index.html (port 5080) that contain the word "Render" or similar
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

print("=== ALL BUTTONS WITH 'Render' ===")
for m in re.finditer(r'<button[^>]*>([\s\S]*?)<\/button>', html):
    full_btn = m.group(0)
    if any(k in full_btn for k in ['Render', 'render', 'Highlight']):
        # extract onclick
        onclick = re.search(r'onclick="([^"]*)"', full_btn)
        oc = onclick.group(1) if onclick else "NO_ONCLICK"
        print(f"ONCLICK: [{oc}] -> TEXT: [{m.group(1).strip()[:40]}]")

