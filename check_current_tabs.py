import re
import json

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all sidebar nav items
nav_matches = re.findall(r'<div class="sidebar-item[^"]*"[^>]*onclick="switchTab\(\'([^\']+)\'\)[^>]*>(.*?)</div>', html, re.DOTALL)
print("Current sidebar items:")
for target, content in nav_matches:
    clean_text = re.sub(r'<[^>]+>', '', content).strip()
    clean_text = ' '.join(clean_text.split())
    print(f" - Tab: {target:15} | Label: {clean_text}")

# Find all pane divs
pane_matches = re.findall(r'<div id="(pane-[^"]+)"', html)
print("\nCurrent pane divs in HTML:", pane_matches)
